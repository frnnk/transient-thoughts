"""
System tray icon (pystray) and unintrusive Windows toast notifications (plyer).
"""

import pystray
from PIL import Image, ImageDraw, ImageFont
from plyer import notification

from transient_thoughts import config


def _create_icon_image():
    img = Image.new("RGB", (64, 64), "#5B8C5A")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "T", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((64 - tw) / 2, (64 - th) / 2 - bbox[1]), "T", fill="white", font=font)
    return img


class TrayIcon:
    def __init__(self, on_prompt, on_view, on_quit):
        self._on_prompt = on_prompt
        self._on_view = on_view
        self._on_quit = on_quit
        self._icon = pystray.Icon(
            name="transient_thoughts",
            icon=_create_icon_image(),
            title=config.APP_NAME,
            menu=pystray.Menu(
                pystray.MenuItem("Open Prompt", self._handle_prompt, default=True),
                pystray.MenuItem("View Entries", self._handle_view),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._handle_quit),
            ),
        )

    # tray callback stubs
    def _handle_prompt(self, icon, item):
        self._on_prompt()
    def _handle_view(self, icon, item):
        self._on_view()
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
