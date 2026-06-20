"""History / Timeline panel (Interim §3.5).

Owner: Janidu. One chronological view of everything the user has done — chats,
appointments, report reviews, prescriptions and future-visit reminders — read
straight from the DB. Strictly read-only: it only SELECTs and renders, never
mutates session state and never calls an agent. Follows the panel contract in
``panels/__init__``.

Note on "medicine searches": pharmacy price lookups are ephemeral by design (not
persisted), so the medicine flow shows up here via its persisted artifact — the
``Prescription`` row — rather than a separate search log.
"""

from __future__ import annotations

import streamlit as st

from ..common import lang_of
from ...db.db import get_conn
from ...i18n.translate import t

_MAX_EVENTS = 50
_CHAT_LIMIT = 15
_DETAIL_TRUNCATE = 160


def _trunc(text: str | None, n: int = _DETAIL_TRUNCATE) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


def _gather_events(user_id: int, lang: str) -> list[dict]:
    """Collect cross-domain activity rows and normalise them into timeline events."""
    conn = get_conn()
    events: list[dict] = []

    for r in conn.execute(
        """SELECT a.booked_at AS ts, s.date, s.time, d.name AS doctor, f.name AS facility
           FROM Appointment a
           JOIN AppointmentSlot s ON s.slot_id = a.slot_id
           JOIN Doctor d ON d.doctor_id = s.doctor_id
           JOIN Facility f ON f.facility_id = d.facility_id
           WHERE a.user_id = ?""",
        (user_id,),
    ).fetchall():
        events.append({
            "ts": r["ts"],
            "icon": "📅",
            "label": t("history.kind_appointment", lang),
            "detail": t("history.appt_detail", lang, doctor=r["doctor"],
                        facility=r["facility"], date=r["date"], time=r["time"]),
        })

    # Only reports that actually completed a panel review (have a ConsensusReport).
    for r in conn.execute(
        """SELECT m.report_id AS id, COALESCE(c.created_at, m.uploaded_at) AS ts
           FROM MedicalReport m
           JOIN ConsensusReport c ON c.report_id = m.report_id
           WHERE m.user_id = ?""",
        (user_id,),
    ).fetchall():
        events.append({
            "ts": r["ts"],
            "icon": "📄",
            "label": t("history.kind_report", lang),
            "detail": t("history.report_detail", lang, id=r["id"]),
        })

    for r in conn.execute(
        "SELECT created_at AS ts, user_confirmed FROM Prescription WHERE user_id = ?",
        (user_id,),
    ).fetchall():
        state = t("history.state_confirmed", lang) if r["user_confirmed"] \
            else t("history.state_unconfirmed", lang)
        events.append({
            "ts": r["ts"],
            "icon": "💊",
            "label": t("history.kind_prescription", lang),
            "detail": t("history.rx_detail", lang, state=state),
        })

    for r in conn.execute(
        """SELECT created_at AS ts, target_date_or_month AS target, notified
           FROM FutureVisitReminder WHERE user_id = ?""",
        (user_id,),
    ).fetchall():
        state = t("history.state_sent", lang) if r["notified"] \
            else t("history.state_pending", lang)
        events.append({
            "ts": r["ts"],
            "icon": "🔔",
            "label": t("history.kind_reminder", lang),
            "detail": t("history.reminder_detail", lang, target=r["target"], state=state),
        })

    for r in conn.execute(
        """SELECT timestamp AS ts, role, content FROM ChatMessage
           WHERE user_id = ? ORDER BY message_id DESC LIMIT ?""",
        (user_id, _CHAT_LIMIT),
    ).fetchall():
        who = t("history.kind_chat_you", lang) if r["role"] == "user" \
            else t("history.kind_chat_bot", lang)
        events.append({
            "ts": r["ts"],
            "icon": "💬",
            "label": who,
            "detail": _trunc(r["content"]),
        })

    # All timestamps share SQLite's 'YYYY-MM-DD HH:MM:SS' format, so a lexical
    # sort is a chronological sort. Most-recent first.
    events.sort(key=lambda e: e["ts"] or "", reverse=True)
    return events[:_MAX_EVENTS]


def render(user: dict) -> None:
    lang = lang_of(user)
    with st.expander(t("history.title", lang), expanded=False):
        events = _gather_events(user["user_id"], lang)
        if not events:
            st.caption(t("history.empty", lang))
            return
        for e in events:
            when = (e["ts"] or "")[:16]
            st.markdown(f"{e['icon']} **{e['label']}** · `{when}`  \n{e['detail']}")
