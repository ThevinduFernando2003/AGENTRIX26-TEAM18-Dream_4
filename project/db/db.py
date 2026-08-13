"""DB connection helper + one-shot init_db().

Default: SQLite file at project/db/app.db.
Optional Phase 1.6: set DATABASE_URL=postgresql://… to use Postgres
(via psycopg + pg_compat shim). CI and local demos stay on SQLite.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

_DB_DIR = Path(__file__).resolve().parent
DB_PATH = _DB_DIR / "app.db"
SCHEMA_PATH = _DB_DIR / "schema.sql"

_local = threading.local()
logger = logging.getLogger("medbridge.db")


def using_postgres() -> bool:
    url = os.environ.get("DATABASE_URL", "").strip().lower()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def get_conn() -> Any:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn
    if using_postgres():
        conn = _connect_postgres()
    else:
        conn = sqlite3.connect(
            DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
    _local.conn = conn
    return conn


def _connect_postgres() -> Any:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL is set but psycopg is not installed. "
            "pip install 'psycopg[binary]>=3.1'"
        ) from exc
    from .pg_compat import PgConnection

    raw = psycopg.connect(os.environ["DATABASE_URL"].strip())
    logger.info("Connected via DATABASE_URL (Postgres)")
    return PgConnection(raw)


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

    # Phase 0: PDPA-style consent timestamp on User (nullable for pre-existing rows).
    user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(User)").fetchall()}
    if "consent_accepted_at" not in user_cols:
        conn.execute("ALTER TABLE User ADD COLUMN consent_accepted_at TEXT")
        conn.commit()
    # Backfill seed/demo users so existing logins remain valid after the column lands.
    conn.execute(
        """UPDATE User SET consent_accepted_at = COALESCE(consent_accepted_at, created_at, datetime('now'))
           WHERE consent_accepted_at IS NULL"""
    )
    conn.commit()

    # Phase 0: pharmacy price freshness.
    pmp_cols = {
        r["name"] for r in conn.execute("PRAGMA table_info(PharmacyMedicinePrice)").fetchall()
    }
    if "updated_at" not in pmp_cols:
        # SQLite disallows non-constant defaults on ADD COLUMN; backfill below.
        conn.execute("ALTER TABLE PharmacyMedicinePrice ADD COLUMN updated_at TEXT")
        conn.commit()
    conn.execute(
        """UPDATE PharmacyMedicinePrice
           SET updated_at = COALESCE(updated_at, datetime('now'))
           WHERE updated_at IS NULL"""
    )
    conn.commit()

    # Phase 0: allow cancelled appointments to retain slot_id history.
    # Old schemas used UNIQUE(slot_id) on the table; rebuild once if needed.
    appt_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='Appointment'"
    ).fetchone()
    needs_rebuild = bool(
        appt_sql
        and appt_sql["sql"]
        and "slot_id" in appt_sql["sql"]
        and "UNIQUE" in appt_sql["sql"].upper()
    )
    if needs_rebuild:
        conn.executescript(
            """
            PRAGMA foreign_keys = OFF;
            CREATE TABLE Appointment__new (
                appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES User(user_id),
                slot_id        INTEGER NOT NULL REFERENCES AppointmentSlot(slot_id),
                status         TEXT NOT NULL DEFAULT 'confirmed',
                booked_at      TEXT DEFAULT (datetime('now'))
            );
            INSERT INTO Appointment__new
                (appointment_id, user_id, slot_id, status, booked_at)
                SELECT appointment_id, user_id, slot_id, status, booked_at FROM Appointment;
            DROP TABLE Appointment;
            ALTER TABLE Appointment__new RENAME TO Appointment;
            PRAGMA foreign_keys = ON;
            """
        )
        conn.commit()
    conn.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_appt_slot_confirmed
           ON Appointment(slot_id) WHERE status = 'confirmed'"""
    )
    conn.commit()

    # Phase 1: RBAC columns on User.
    user_cols = {r["name"] for r in conn.execute("PRAGMA table_info(User)").fetchall()}
    if "role" not in user_cols:
        conn.execute("ALTER TABLE User ADD COLUMN role TEXT DEFAULT 'patient'")
        conn.commit()
    if "pharmacy_id" not in user_cols:
        conn.execute("ALTER TABLE User ADD COLUMN pharmacy_id INTEGER")
        conn.commit()
    if "facility_id" not in user_cols:
        conn.execute("ALTER TABLE User ADD COLUMN facility_id INTEGER")
        conn.commit()
    conn.execute("UPDATE User SET role = COALESCE(role, 'patient') WHERE role IS NULL OR role = ''")
    conn.commit()

    # Lift legacy SupplierAccount rows into User (pharmacy→pharmacy_staff, etc.).
    has_supplier = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='SupplierAccount'"
    ).fetchone()
    if has_supplier:
        for r in conn.execute(
            """SELECT username, password_hash, role, pharmacy_id, facility_id
               FROM SupplierAccount"""
        ).fetchall():
            exists = conn.execute(
                "SELECT user_id FROM User WHERE username = ?", (r["username"],)
            ).fetchone()
            mapped = (
                "pharmacy_staff"
                if r["role"] == "pharmacy"
                else "hospital_staff"
                if r["role"] == "hospital"
                else "patient"
            )
            if exists:
                conn.execute(
                    """UPDATE User SET role = ?, pharmacy_id = COALESCE(?, pharmacy_id),
                           facility_id = COALESCE(?, facility_id)
                       WHERE user_id = ?""",
                    (mapped, r["pharmacy_id"], r["facility_id"], exists["user_id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO User(username, password_hash, role, pharmacy_id, facility_id,
                                        consent_accepted_at)
                       VALUES(?,?,?,?,?,datetime('now'))""",
                    (
                        r["username"],
                        r["password_hash"],
                        mapped,
                        r["pharmacy_id"],
                        r["facility_id"],
                    ),
                )
        conn.commit()


def init_db(seed: bool = True) -> None:
    """Create tables if missing and (optionally) load seed data."""
    conn = get_conn()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        script = f.read()
    if using_postgres():
        conn.executescript(script)
        # SQLite-specific PRAGMA migrations do not apply; schema.sql is source of truth.
    else:
        conn.executescript(script)
        conn.commit()
        _migrate(conn)
    if seed:
        from .seed import ensure_staff_accounts, load_seed_if_empty  # local import to avoid cycle
        load_seed_if_empty()
        # Staff accounts can land on DBs that already had patient seed.
        ensure_staff_accounts()


if __name__ == "__main__":
    init_db()
    target = "Postgres (DATABASE_URL)" if using_postgres() else str(DB_PATH)
    print(f"DB initialized at {target}")
