"""Future-visit reminders — detection regex, 7-day windowing, fire() marks notified."""

from __future__ import annotations

import datetime

from project.agents import basic_chatbot as bc
from project.agents import reminders

_TODAY = datetime.date(2026, 1, 15)


def test_detect_reminder_variants():
    assert bc.detect_reminder("follow up in 3 days", today=_TODAY) == "2026-01-18"
    assert bc.detect_reminder("come back in 2 weeks", today=_TODAY) == "2026-01-29"
    assert bc.detect_reminder("come back in one month", today=_TODAY) == "2026-02"  # YYYY-MM
    assert bc.detect_reminder("come back on 2026-08-01", today=_TODAY) == "2026-08-01"
    assert bc.detect_reminder("return next month", today=_TODAY) == "2026-02"
    assert bc.detect_reminder("just saying hello", today=_TODAY) is None


def test_due_within_windowing(seeded_db):
    conn = seeded_db.get_conn()
    near = (_TODAY + datetime.timedelta(days=3)).isoformat()
    far = (_TODAY + datetime.timedelta(days=30)).isoformat()
    conn.execute(
        "INSERT INTO FutureVisitReminder(user_id, target_date_or_month, notified) VALUES(2,?,0)",
        (near,),
    )
    conn.execute(
        "INSERT INTO FutureVisitReminder(user_id, target_date_or_month, notified) VALUES(2,?,0)",
        (far,),
    )
    conn.commit()

    targets = {d["target_date_or_month"] for d in reminders.due_within(2, days=7, today=_TODAY)}
    assert near in targets
    assert far not in targets


def test_fire_marks_notified_and_is_idempotent(seeded_db, monkeypatch):
    # Mock the push so the test is deterministic regardless of network access.
    monkeypatch.setattr(reminders, "ntfy_send", lambda **kwargs: True)
    conn = seeded_db.get_conn()
    cur = conn.execute(
        "INSERT INTO FutureVisitReminder(user_id, target_date_or_month, notified) VALUES(3,?,0)",
        ("2026-02-01",),
    )
    conn.commit()
    rid = cur.lastrowid

    assert reminders.fire(3, [rid]) == 1
    row = conn.execute(
        "SELECT notified FROM FutureVisitReminder WHERE reminder_id = ?", (rid,)
    ).fetchone()
    assert row["notified"] == 1
    # Already notified → firing again sends nothing.
    assert reminders.fire(3, [rid]) == 0
