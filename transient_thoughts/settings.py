"""
Persisted user settings (frequency, notifications, placement, quiet hours).

Stored as JSON in the same APPDATA directory as the SQLite DB. Missing or
malformed files fall back to defaults; unknown keys are ignored so older
installs survive new fields being added.
"""

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

from transient_thoughts import config

PLACEMENTS = ("center", "top-left", "top-right", "bottom-left", "bottom-right")

# Timezones offered for interpreting quiet-hours bounds. "local" means the
# system's local timezone. The rest are IANA names that zoneinfo resolves.
TIMEZONES = (
    "local",
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Anchorage",
    "America/Honolulu",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Moscow",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Pacific/Auckland",
)


@dataclass
class Settings:
    interval_minutes: int = 30
    notifications_enabled: bool = True
    placement: str = "center"
    quiet_hours_enabled: bool = False
    quiet_start_hour: int = 22  # 24-hour, inclusive start
    quiet_end_hour: int = 7     # 24-hour, exclusive end
    quiet_hours_timezone: str = "local"


SETTINGS_PATH: Path = config.DB_DIR / "settings.json"


def load() -> Settings:
    if not SETTINGS_PATH.exists():
        return Settings()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    fields = Settings.__dataclass_fields__
    return Settings(**{k: v for k, v in data.items() if k in fields})


def save(settings: Settings) -> None:
    # Atomic write: dump to a temp file in the same directory, then os.replace()
    # it over the target. os.replace is an atomic rename on POSIX and Windows,
    # so a concurrent/crashing reader always sees either the complete old file
    # or the complete new one — never a half-written settings.json.
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = SETTINGS_PATH.with_name(SETTINGS_PATH.name + ".tmp")
    tmp_path.write_text(
        json.dumps(asdict(settings), indent=2),
        encoding="utf-8",
    )
    os.replace(tmp_path, SETTINGS_PATH)
