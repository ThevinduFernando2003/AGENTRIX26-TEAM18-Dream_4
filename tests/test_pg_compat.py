"""Postgres compat helpers — offline (no live DATABASE_URL required)."""

from __future__ import annotations

import os

from project.db import db
from project.db.pg_compat import qmark_to_percent, sqlite_ddl_to_postgres


def test_using_postgres_false_by_default(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert db.using_postgres() is False


def test_using_postgres_detects_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/medbridge")
    assert db.using_postgres() is True
    monkeypatch.setenv("DATABASE_URL", "sqlite:///nope")
    assert db.using_postgres() is False


def test_qmark_and_ddl_rewrite():
    assert qmark_to_percent("SELECT * FROM T WHERE a = ? AND b = ?") == (
        "SELECT * FROM T WHERE a = %s AND b = %s"
    )
    ddl = sqlite_ddl_to_postgres(
        "PRAGMA foreign_keys = ON;\n"
        "CREATE TABLE X (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT DEFAULT (datetime('now')));"
    )
    assert "PRAGMA" not in ddl.upper()
    assert "SERIAL PRIMARY KEY" in ddl
    assert "CURRENT_TIMESTAMP" in ddl
