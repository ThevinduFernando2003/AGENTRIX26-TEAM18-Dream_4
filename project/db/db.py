"""SQLite connection helper + one-shot init_db().

A single SQLite file lives at project/db/app.db. Connections are
per-thread because Streamlit reruns scripts on a single thread per
session but background callbacks may not be.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

_DB_DIR = Path(__file__).resolve().parent
DB_PATH = _DB_DIR / "app.db"
SCHEMA_PATH = _DB_DIR / "schema.sql"

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        _local.conn = conn
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight, idempotent migrations for DBs created before a schema change."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(ChatMessage)").fetchall()}
    if "conversation_id" not in cols:
        conn.execute("ALTER TABLE ChatMessage ADD COLUMN conversation_id INTEGER")
        conn.commit()
    # Safe to create now that the column is guaranteed to exist.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_conversation ON ChatMessage(conversation_id, message_id)"
    )
    conn.commit()

    # Fold any pre-existing messages (no conversation yet) into one thread per user
    # so old chats still show up in the new conversation sidebar.
    orphan_users = [
        r["user_id"]
        for r in conn.execute(
            "SELECT DISTINCT user_id FROM ChatMessage WHERE conversation_id IS NULL"
        ).fetchall()
    ]
    for uid in orphan_users:
        cur = conn.execute(
            "INSERT INTO Conversation(user_id, title) VALUES(?, 'Earlier chat')", (uid,)
        )
        conn.execute(
            "UPDATE ChatMessage SET conversation_id = ? WHERE user_id = ? AND conversation_id IS NULL",
            (cur.lastrowid, uid),
        )
    if orphan_users:
        conn.commit()


def init_db(seed: bool = True) -> None:
    """Create tables if missing and (optionally) load seed data."""
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    _migrate(conn)
    if seed:
        from .seed import load_seed_if_empty  # local import to avoid cycle
        load_seed_if_empty()


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
