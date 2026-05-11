"""
System tray icon (pystray) and unintrusive Windows toast notifications.

Toasts use `windows-toasts` (native WinRT) on Windows so we get our custom
app name, our app icon, and a click handler that opens the prompt panel.
Non-Windows platforms fall back to `plyer` notifications without click support.
"""

import sys

import pystray
from PIL import Image, ImageDraw
from plyer import notification

from transient_thoughts import config

# Palette mirrored from ui.py so the tray reads as part of the same set.
_RING = "#D9D4C7"   # light tan outer ring
_DOT = "#8A8680"    # muted gray-tan center dot (visible on light + dark taskbars)

# Stable Application User Model ID. Registered in HKCU so toasts attribute
# themselves to "Transient Thoughts" instead of the host Python interpreter.
_AUMID = "TransientThoughts.App"


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


def _register_aumid(aumid: str, display_name: str, icon_path):
    """Register the Application User Model ID under HKCU so Windows attributes
    toast notifications to our app name + icon. Idempotent; safe to call on
    every launch. No-op on non-Windows or if registry access fails."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        key_path = rf"Software\Classes\AppUserModelId\{aumid}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, display_name)
            if icon_path is not None:
                winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon_path))
                # IconBackgroundColor is required by some Windows versions to
                # render the icon; transparent ("0") lets our PNG show as-is.
                winreg.SetValueEx(key, "IconBackgroundColor", 0, winreg.REG_SZ, "0")
    except Exception:
        pass


def _write_toast_icon():
    """Render the tray icon as a PNG on disk so toast notifications can reference
    it as their AppLogo override. Returns the path, or None on failure."""
    path = config.DB_DIR / "tray_icon.png"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Render at a larger size so the toast's high-DPI AppLogo stays crisp.
        size = 256
        scale = 4
        big = size * scale
        img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        ring_pad = int(24 * scale)
        ring_width = int(12 * scale)
        draw.ellipse(
            [ring_pad, ring_pad, big - ring_pad, big - ring_pad],
            outline=_RING, width=ring_width,
        )
        dot_pad = int(88 * scale)
        draw.ellipse(
            [dot_pad, dot_pad, big - dot_pad, big - dot_pad],
            fill=_DOT,
        )
        img.resize((size, size), Image.LANCZOS).save(str(path), format="PNG")
    except Exception:
        return None
    return path


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

        # Build the Windows toast pipeline if available. Failures degrade to plyer.
        self._toast_icon_path = _write_toast_icon()
        _register_aumid(_AUMID, config.APP_NAME, self._toast_icon_path)
        self._toaster = None
        if sys.platform == "win32":
            try:
                from windows_toasts import WindowsToaster
                self._toaster = WindowsToaster(_AUMID)
            except Exception:
                self._toaster = None

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
        if self._toaster is not None:
            try:
                from windows_toasts import (
                    Toast, ToastDisplayImage, ToastImagePosition,
                )
                images = []
                if self._toast_icon_path is not None:
                    images.append(ToastDisplayImage.fromPath(
                        str(self._toast_icon_path),
                        position=ToastImagePosition.AppLogo,
                        circleCrop=True,
                    ))
                toast = Toast(
                    text_fields=[title, message],
                    images=images,
                    on_activated=lambda _args: self._on_prompt(),
                )
                self._toaster.show_toast(toast)
                return
            except Exception:
                pass
        # Cross-platform / fallback path (no click support).
        try:
            notification.notify(
                title=title,
                message=message,
                app_name=config.APP_NAME,
                timeout=10,
            )
        except Exception:
            pass
