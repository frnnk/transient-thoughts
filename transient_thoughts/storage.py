"""
SQLite persistence layer. Owns the thoughts table and all read/write operations.
"""

import sqlite3
import pathlib
from datetime import datetime, timezone
from transient_thoughts import config


class ThoughtStorage:
    def __init__(self, db_path: pathlib.Path = config.DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS thoughts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def add(self, text: str) -> int:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO thoughts (timestamp, text) VALUES (?, ?)",
                (ts, text),
            )
            return cursor.lastrowid

    def get_all(self, limit: int = 500) -> list[tuple[int, str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, text FROM thoughts ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return rows

    def get_range(self, start: str, end: str) -> list[tuple[int, str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, timestamp, text FROM thoughts "
                "WHERE timestamp >= ? AND timestamp <= ? ORDER BY id DESC",
                (start, end),
            ).fetchall()
        return rows
