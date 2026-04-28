"""
App orchestrator that wires storage, UI, and the tray together as well as manages timer thread.
"""

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

    def start(self):
        self._tray = TrayIcon(
            on_prompt=self._on_prompt,
            on_view=self._on_view,
            on_quit=self._on_quit,
        )
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
        self._tray.run()  # blocks

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
                ui.show_input_window(self._on_submit)
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
