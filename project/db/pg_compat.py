"""Minimal SQLite→Postgres compatibility shim (Phase 1.6).

Translates ``?`` placeholders to ``%s`` and exposes a sqlite-like
``execute`` / ``executescript`` / context-manager transaction API on top of
psycopg. Used only when ``DATABASE_URL`` is set.
"""

from __future__ import annotations

import re
from typing import Any, Sequence


def qmark_to_percent(sql: str) -> str:
    """Replace unbound ``?`` placeholders with ``%s`` (ignore ``??``)."""
    out: list[str] = []
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "?":
            if i + 1 < len(sql) and sql[i + 1] == "?":
                out.append("?")
                i += 2
                continue
            out.append("%s")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


_AUTOINCREMENT = re.compile(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", re.I)
_DATETIME_NOW = re.compile(r"datetime\('now'\)", re.I)


def sqlite_ddl_to_postgres(sql: str) -> str:
    """Best-effort rewrite of our schema.sql dialect for Postgres."""
    s = sql
    s = re.sub(r"PRAGMA\s+[^;]+;", "", s, flags=re.I)
    s = _AUTOINCREMENT.sub("SERIAL PRIMARY KEY", s)
    s = _DATETIME_NOW.sub("CURRENT_TIMESTAMP", s)
    return s


class PgRow(dict):
    """dict row that also supports integer index access like sqlite3.Row."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class PgConnection:
    def __init__(self, raw: Any):
        self._raw = raw

    def execute(self, sql: str, params: Sequence[Any] = ()):
        cur = self._raw.cursor()
        rewritten = qmark_to_percent(_DATETIME_NOW.sub("CURRENT_TIMESTAMP", sql))
        # Prefer RETURNING for INSERT so lastrowid works like SQLite.
        is_insert = rewritten.lstrip().upper().startswith("INSERT")
        if is_insert and "RETURNING" not in rewritten.upper():
            rewritten = rewritten.rstrip().rstrip(";") + " RETURNING *"
        cur.execute(rewritten, tuple(params))
        return PgCursor(cur, conn=self._raw, was_insert=is_insert)

    def executescript(self, script: str) -> None:
        rewritten = sqlite_ddl_to_postgres(script)
        statements = [s.strip() for s in rewritten.split(";") if s.strip()]
        with self._raw.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        self._raw.commit()

    def commit(self) -> None:
        self._raw.commit()

    def close(self) -> None:
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()
        return False


class PgCursor:
    def __init__(self, cur: Any, *, conn: Any = None, was_insert: bool = False):
        self._cur = cur
        self.lastrowid = None
        if was_insert and cur.description:
            row = cur.fetchone()
            if row is not None:
                # First column is typically the serial PK.
                if hasattr(row, "keys"):
                    keys = list(row.keys())
                    self.lastrowid = row[keys[0]]
                    self._buffered = PgRow({k: row[k] for k in keys})
                else:
                    self.lastrowid = row[0]
                    cols = [d.name for d in cur.description]
                    self._buffered = PgRow(dict(zip(cols, row)))
                return
        self._buffered = None

    def fetchone(self):
        if self._buffered is not None:
            row = self._buffered
            self._buffered = None
            return row
        row = self._cur.fetchone()
        if row is None:
            return None
        if hasattr(row, "keys"):
            return PgRow({k: row[k] for k in row.keys()})
        cols = [d.name for d in self._cur.description]
        return PgRow(dict(zip(cols, row)))

    def fetchall(self):
        rows = []
        first = self.fetchone()
        if first is not None:
            rows.append(first)
        while True:
            row = self._cur.fetchone()
            if row is None:
                break
            if hasattr(row, "keys"):
                rows.append(PgRow({k: row[k] for k in row.keys()}))
            else:
                cols = [d.name for d in self._cur.description]
                rows.append(PgRow(dict(zip(cols, row))))
        return rows
