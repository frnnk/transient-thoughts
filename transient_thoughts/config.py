"""
Application-wide constants and defaults (DB path, app name, prompt interval).
"""

import os
import pathlib

APP_NAME = "Transient Thoughts"

# Folder where the SQLite database lives, defaults to %APPDATA%\transient-thoughts on
# Windows, or ~/transient-thoughts elsewhere. Change to relocate stored data.
DB_DIR = pathlib.Path(
    os.environ.get("APPDATA", str(pathlib.Path.home()))
) / "transient-thoughts"
DB_PATH = DB_DIR / "thoughts.db"

# Minutes between notifications nudging the user to record a thought. Can also be 
# overridden at runtime via --interval.
DEFAULT_INTERVAL_MINUTES = 30
