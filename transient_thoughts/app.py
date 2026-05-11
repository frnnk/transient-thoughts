"""
App orchestrator that wires storage, UI, and the tray together as well as manages timer thread.
"""

import sys
import threading
from transient_thoughts import config
from transient_thoughts import ui
from transient_thoughts.storage import ThoughtStorage
from transient_thoughts.tray import TrayIcon


class TransientThoughtsApp:
    def __init__(self, interval_minutes: int = config.DEFAULT_INTERVAL_MINUTES):
        self.storage = ThoughtStorage()
        self.interval = interval_minutes * 60
        self._prompt_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._ctrl_handler_ref = None  # holds the Windows ctypes callback alive

    def start(self):
        self._tray = TrayIcon(
            on_prompt=self._on_prompt,
            on_view=self._on_view,
            on_quit=self._on_quit,
        )
        self._install_interrupt_handler()
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

    def _timer_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.interval)
            if self._stop_event.is_set():
                break
            self._tray.send_notification(
                "Time for a thought",
                "Click the tray icon to jot something down.",
            )

    def _on_prompt(self):
        if not self._prompt_lock.acquire(blocking=False):
            return

        def _run():
            try:
                ui.show_input_window(
                    self._on_submit,
                    on_view=self._on_view,
                    on_quit=self._on_quit,
                )
            finally:
                self._prompt_lock.release()

        threading.Thread(target=_run, daemon=True).start()

    def _on_submit(self, text: str):
        self.storage.add(text)

    def _on_view(self):
        def _run():
            entries = self.storage.get_all()
            ui.show_viewer_window(entries)

        threading.Thread(target=_run, daemon=True).start()

    def _on_quit(self):
        self._stop_event.set()
        self._tray.stop()
