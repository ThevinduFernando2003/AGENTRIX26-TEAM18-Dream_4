"""Thin repository seam (Phase 1.5) — domain code should prefer this over raw DB access.

Today this wraps SQLite via ``get_conn()``. Phase 1.6 may swap the underlying
driver when ``DATABASE_URL`` is set; call sites stay stable.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from .db import get_conn


def connection():
    """Return the thread-local DB connection (SQLite or future Postgres)."""
    return get_conn()


@contextmanager
def transaction() -> Iterator[Any]:
    """Commit on success, roll back on error (sqlite3 Connection context mgr)."""
    conn = get_conn()
    with conn:
        yield conn


def fetchall(sql: str, params: Sequence[Any] = ()) -> list[Any]:
    return list(get_conn().execute(sql, params).fetchall())


def fetchone(sql: str, params: Sequence[Any] = ()) -> Any | None:
    return get_conn().execute(sql, params).fetchone()


def execute(sql: str, params: Sequence[Any] = ()) -> Any:
    """Execute and commit immediately (non-transactional single statement)."""
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur
