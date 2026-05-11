"""
System tray icon (pystray) and unintrusive Windows toast notifications (plyer).
"""

import pystray
from PIL import Image, ImageDraw
from plyer import notification

from transient_thoughts import config

# Palette mirrored from ui.py so the tray reads as part of the same set.
_RING = "#D9D4C7"   # light tan outer ring
_DOT = "#8A8680"    # muted gray-tan center dot (visible on light + dark taskbars)


def _create_icon_image():
    """A soft tan ring with a muted center dot — visual echo of the panel's
    header bullet. Drawn supersampled and downsampled so the circles stay smooth
    at the tray's 16x16 render size."""
    size = 64
    scale = 4
    big_size = size * scale
    img = Image.new("RGBA", (big_size, big_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    ring_pad = 6 * scale
    ring_width = 3 * scale
    draw.ellipse(
        [ring_pad, ring_pad, big_size - ring_pad, big_size - ring_pad],
        outline=_RING, width=ring_width,
    )

    dot_pad = 22 * scale
    draw.ellipse(
        [dot_pad, dot_pad, big_size - dot_pad, big_size - dot_pad],
        fill=_DOT,
    )

    return img.resize((size, size), Image.LANCZOS)


class TrayIcon:
    def __init__(self, on_prompt, on_view, on_quit, on_settings=None):
        self._on_prompt = on_prompt
        self._on_view = on_view
        self._on_settings = on_settings
        self._on_quit = on_quit
        items = [
            pystray.MenuItem("Open Prompt", self._handle_prompt, default=True),
            pystray.MenuItem("View Entries", self._handle_view),
        ]
        if on_settings is not None:
            items.append(pystray.MenuItem("Settings", self._handle_settings))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self._handle_quit))
        self._icon = pystray.Icon(
            name="transient_thoughts",
            icon=_create_icon_image(),
            title=config.APP_NAME,
            menu=pystray.Menu(*items),
        )

    # tray callback stubs
    def _handle_prompt(self, icon, item):
        self._on_prompt()
    def _handle_view(self, icon, item):
        self._on_view()
    def _handle_settings(self, icon, item):
        if self._on_settings is not None:
            self._on_settings()
    def _handle_quit(self, icon, item):
        self._on_quit()

    def run(self):
        self._icon.run()

    def stop(self):
        self._icon.stop()

    def send_notification(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name=config.APP_NAME,
                timeout=10,
            )
        except Exception:
            pass
