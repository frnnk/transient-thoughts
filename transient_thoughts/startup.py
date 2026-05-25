"""
Windows-only helpers to register/unregister Transient Thoughts as a login
startup program via HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run.

We point the Run entry at transient-thoughts-gui.exe (the gui-script wrapper,
which Hatch builds against pythonw.exe) so no console window appears at login.
"""

import shutil
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "TransientThoughts"  # visible label in Task Manager > Startup


def _gui_exe_path() -> str | None:
    """Locate transient-thoughts-gui.exe on PATH. uv tool install drops it in
    %USERPROFILE%\\.local\\bin (or equivalent) and adds that dir to PATH."""
    return shutil.which("transient-thoughts-gui")


def _is_inside_venv(exe: str) -> bool:
    """A venv root contains pyvenv.cfg by definition. The exe sits in <root>/Scripts,
    so check the grandparent. Works for any venv name (not just `.venv`)."""
    return (Path(exe).parent.parent / "pyvenv.cfg").exists()


def register() -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "--setup-startup is Windows-only."
    exe = _gui_exe_path()
    if exe is None:
        return False, (
            "Could not find transient-thoughts-gui.exe on PATH. "
            "Install first with: uv tool install --reinstall git+https://github.com/frnnk/transient-thoughts"
        )
    if _is_inside_venv(exe):
        return False, (
            f"Refusing to register a venv-local path ({exe}).\n"
            "That path will break if the venv is rebuilt or the project is moved.\n"
            "For login auto-start, install the tool globally first:\n"
            "  uv tool install --reinstall git+https://github.com/frnnk/transient-thoughts\n"
            "Then re-run --setup-startup outside of `uv run`."
        )
    import winreg
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        # Quote the path so a "Program Files"-style location survives tokenization.
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, f'"{exe}"')
    return True, f"Registered to run at login: {exe}"


def unregister() -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "--remove-startup is Windows-only."
    import winreg
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        return True, "No startup entry was registered."
    return True, "Startup entry removed."
