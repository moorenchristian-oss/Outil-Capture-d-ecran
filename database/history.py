import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "screen_capture_tool" / "history.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    filename TEXT NOT NULL,
    extracted_text TEXT,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def add_entry(entry_type: str, filename: str, extracted_text: str = ""):
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT INTO captures (type, filename, extracted_text, created_at) VALUES (?, ?, ?, ?)",
            (entry_type, filename, extracted_text, datetime.now().isoformat()),
        )
    conn.close()


def list_entries():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, type, filename, extracted_text, created_at FROM captures ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows
