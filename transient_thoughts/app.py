"""
App orchestrator that wires storage, UI, and the tray together as well as manages timer thread.
"""

import sys
import threading
from datetime import datetime
from transient_thoughts import config
from transient_thoughts import ui
from transient_thoughts import settings as settings_module
from transient_thoughts.storage import ThoughtStorage
from transient_thoughts.tray import TrayIcon


class TransientThoughtsApp:
    def __init__(self, interval_minutes: int | None = None):
        self.storage = ThoughtStorage()
        self.settings = settings_module.load()
        # CLI --interval overrides the persisted setting and is itself persisted,
        # so the next launch (without flags) keeps the same cadence.
        if interval_minutes is not None and interval_minutes != self.settings.interval_minutes:
            self.settings.interval_minutes = interval_minutes
            settings_module.save(self.settings)
        self._prompt_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._ctrl_handler_ref = None  # holds the Windows ctypes callback alive
        self._hotkey_listener = None   # pynput GlobalHotKeys listener, started in start()

    def start(self):
        self._tray = TrayIcon(
            on_prompt=self._on_prompt,
            on_view=self._on_view,
            on_settings=self._on_settings,
            on_quit=self._on_quit,
        )
        self._install_interrupt_handler()
        self._install_global_hotkey()
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        self._tray.run()  # blocks

    def _install_interrupt_handler(self):
        """Route Ctrl+C (and other terminal-driven shutdown signals) through the
        same graceful path as the tray's Quit menu, so closing from the command
        line tears down the tray icon and timer thread cleanly."""
        def trigger_quit():
            # Run the shutdown off-handler so the OS callback returns promptly
            # and pystray.stop() can be invoked without re-entering the pump.
            threading.Thread(target=self._on_quit, daemon=True).start()

        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            HANDLER = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
            # CTRL_C=0, CTRL_BREAK=1, CTRL_CLOSE=2, CTRL_LOGOFF=5, CTRL_SHUTDOWN=6
            handled = {0, 1, 2, 5, 6}
            def _handler(ctrl_type):
                if ctrl_type in handled:
                    trigger_quit()
                    return True
                return False
            self._ctrl_handler_ref = HANDLER(_handler)
            ctypes.windll.kernel32.SetConsoleCtrlHandler(self._ctrl_handler_ref, True)
        else:
            import signal
            def _handler(signum, frame):
                trigger_quit()
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)

    def _install_global_hotkey(self):
        """Register a system-wide hotkey that opens the entry panel from anywhere.
        pynput runs the listener in its own thread; _on_prompt is already
        re-entrancy-safe via _prompt_lock so duplicate presses are harmless."""
        try:
            from pynput import keyboard
        except ImportError:
            return  # hotkey is a nice-to-have; don't crash if pynput is missing
        try:
            self._hotkey_listener = keyboard.GlobalHotKeys({
                config.GLOBAL_HOTKEY: self._on_prompt,
            })
            self._hotkey_listener.start()
        except Exception:
            # OS may refuse the binding (e.g. another app owns it). Silent-fail
            # rather than blocking startup — user still has tray + toast paths.
            self._hotkey_listener = None

    def _timer_loop(self):
        while not self._stop_event.is_set():
            wait_seconds = max(60, self.settings.interval_minutes * 60)
            self._stop_event.wait(timeout=wait_seconds)
            if self._stop_event.is_set():
                break
            if not self.settings.notifications_enabled:
                continue
            if self._is_in_quiet_hours():
                continue
            self._tray.send_notification(
                "Time for a thought",
                "Click the tray icon to jot something down.",
            )

    def _is_in_quiet_hours(self) -> bool:
        if not self.settings.quiet_hours_enabled:
            return False
        tz_name = self.settings.quiet_hours_timezone
        if tz_name and tz_name != "local":
            try:
                from zoneinfo import ZoneInfo
                now_h = datetime.now(ZoneInfo(tz_name)).hour
            except Exception:
                # Unknown timezone or missing tzdata — fall back to local time.
                now_h = datetime.now().hour
        else:
            now_h = datetime.now().hour
        start, end = self.settings.quiet_start_hour, self.settings.quiet_end_hour
        if start == end:
            return False
        if start < end:
            return start <= now_h < end
        # Wraps midnight (e.g. 22 → 7).
        return now_h >= start or now_h < end

    def _on_prompt(self):
        if not self._prompt_lock.acquire(blocking=False):
            return

        def _run():
            try:
                ui.show_input_window(
                    self._on_submit,
                    on_view=self._on_view,
                    on_quit=self._on_quit,
                    on_settings=self._on_settings,
                    placement=self.settings.placement,
                )
            finally:
                self._prompt_lock.release()

        threading.Thread(target=_run, daemon=True).start()

    def _on_submit(self, text: str):
        self.storage.add(text)

    def _on_view(self):
        def _run():
            entries = self.storage.get_all()
            ui.show_viewer_window(entries, on_settings=self._on_settings)

        threading.Thread(target=_run, daemon=True).start()

    def _on_settings(self):
        def _run():
            ui.show_settings_window(self.settings, self._on_settings_save)

        threading.Thread(target=_run, daemon=True).start()

    def _on_settings_save(self, new_settings):
        self.settings = new_settings
        settings_module.save(new_settings)

    def _on_quit(self):
        self._stop_event.set()
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
        self._tray.stop()
