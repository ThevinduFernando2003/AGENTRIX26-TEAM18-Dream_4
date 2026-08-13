"""Future-visit reminder service.

Provides:

- `due_within(user_id, days=7)` — reminders whose target date/month
  falls within the next N days and haven't been notified yet.
- `due_all(days=7)` — same window across all users (for the worker).
- `fire(user_id, reminder_ids)` — send one ntfy push per reminder,
  mark `notified=1`. Idempotent: already-notified rows are ignored.
- `process_due(days=7)` — fire every due reminder once (worker + tests).

The sidebar "Check my reminders" button remains a manual override.
`project/workers/reminder_worker.py` polls `process_due` on an interval.

`target_date_or_month` is stored as either `YYYY-MM-DD` (specific day)
or `YYYY-MM` (month-only). For month-only we treat the 1st of the
month as the trigger.
"""

from __future__ import annotations

import logging
from datetime import date as dtdate, timedelta
from typing import Optional

from ..db.db import get_conn
from ..notifications.ntfy_client import send as ntfy_send, topic_for_user

logger = logging.getLogger("medbridge.reminders")


def _parse_target(target: str) -> Optional[dtdate]:
    target = (target or "").strip()
    if not target:
        return None
    try:
        if len(target) == 7:  # YYYY-MM
            y, m = target.split("-")
            return dtdate(int(y), int(m), 1)
        return dtdate.fromisoformat(target)
    except (ValueError, IndexError):
        return None


def list_for_user(user_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT reminder_id, doctor_id, target_date_or_month, notified, created_at
           FROM FutureVisitReminder
           WHERE user_id = ?
           ORDER BY target_date_or_month""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def due_within(user_id: int, days: int = 7, today: Optional[dtdate] = None) -> list[dict]:
    today = today or dtdate.today()
    horizon = today + timedelta(days=days)
    out: list[dict] = []
    for row in list_for_user(user_id):
        if row["notified"]:
            continue
        target = _parse_target(row["target_date_or_month"])
        if target is None:
            continue
        if today <= target <= horizon:
            out.append({**row, "user_id": user_id, "_target_date": target.isoformat()})
    return out


def due_all(days: int = 7, today: Optional[dtdate] = None) -> list[dict]:
    """Un-notified reminders due within the window for every user."""
    today = today or dtdate.today()
    horizon = today + timedelta(days=days)
    conn = get_conn()
    rows = conn.execute(
        """SELECT reminder_id, user_id, doctor_id, target_date_or_month, notified, created_at
           FROM FutureVisitReminder
           WHERE notified = 0
           ORDER BY user_id, target_date_or_month"""
    ).fetchall()
    out: list[dict] = []
    for row in rows:
        target = _parse_target(row["target_date_or_month"])
        if target is None:
            continue
        if today <= target <= horizon:
            out.append({**dict(row), "_target_date": target.isoformat()})
    return out


def process_due(days: int = 7, today: Optional[dtdate] = None) -> int:
    """Fire all due reminders across users. Returns total pushes sent."""
    by_user: dict[int, list[int]] = {}
    for row in due_all(days=days, today=today):
        by_user.setdefault(row["user_id"], []).append(row["reminder_id"])
    total = 0
    for uid, ids in by_user.items():
        total += fire(uid, ids)
    return total


def fire(user_id: int, reminder_ids: list[int]) -> int:
    """Send pushes for the given reminder ids. Returns the number sent."""
    if not reminder_ids:
        return 0
    conn = get_conn()
    placeholders = ",".join("?" * len(reminder_ids))
    rows = conn.execute(
        f"""SELECT reminder_id, target_date_or_month, doctor_id
            FROM FutureVisitReminder
            WHERE user_id = ? AND notified = 0 AND reminder_id IN ({placeholders})""",
        (user_id, *reminder_ids),
    ).fetchall()

    topic = topic_for_user(user_id)
    sent = 0
    for r in rows:
        msg = (
            f"Reminder: your follow-up is scheduled around "
            f"{r['target_date_or_month']}. Open MedBridge AI to book a slot."
        )
        ok = ntfy_send(
            topic=topic,
            title="MedBridge AI: follow-up reminder",
            message=msg,
            user_id=user_id,
            tags=["bell"],
            notif_type="reminder",
        )
        if ok:
            conn.execute(
                "UPDATE FutureVisitReminder SET notified = 1 WHERE reminder_id = ?",
                (r["reminder_id"],),
            )
            sent += 1
    conn.commit()
    return sent
