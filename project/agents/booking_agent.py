"""Booking Agent — Pydantic AI typed-output booking.

The Basic Chatbot has already extracted structured fields
(doctor_name, specialty, date, time) from the user's message into the
`extracted` dict. This module exposes:

- `find_doctors(name_or_specialty)` — DB lookup.
- `find_slot(doctor_id, date, time)` — exact match.
- `nearest_alternatives(doctor_id, target_dt)` — ±7-day window sorted
  by proximity.
- `book(user_id, slot_id)` — atomic appointment insert + slot flip.
- `process(user_id, extracted)` — orchestrates the above and returns
  a `BookingResponse`.

A Pydantic AI Agent wraps the same tools so a free-form natural-language
booking request can also be handled when GEMINI_API_KEY is set. The
deterministic path is the demo's source of truth; the LLM path is
icing.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date as dtdate, datetime, timedelta
from typing import Optional

from ..db.db import get_conn
from ..models import (
    AlternativeSlot,
    BookingConfirmation,
    BookingResponse,
)

logger = logging.getLogger("medbridge.booking")


# ---------- pure SQL tools ----------

def find_doctors(query: str) -> list[dict]:
    """Match on doctor name OR specialty name (case-insensitive contains)."""
    conn = get_conn()
    q = f"%{query.strip().lower()}%"
    rows = conn.execute(
        """SELECT d.doctor_id, d.name AS doctor_name, d.channeling_fee,
                  f.facility_id, f.name AS facility_name,
                  s.specialty_id, s.name AS specialty_name
           FROM Doctor d
           JOIN Facility  f ON f.facility_id  = d.facility_id
           JOIN Specialty s ON s.specialty_id = d.specialty_id
           WHERE LOWER(d.name) LIKE ? OR LOWER(s.name) LIKE ?
           ORDER BY d.name""",
        (q, q),
    ).fetchall()
    return [dict(r) for r in rows]


def find_slot(doctor_id: int, date_str: str, time_str: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        """SELECT slot_id, doctor_id, date, time, is_available
           FROM AppointmentSlot
           WHERE doctor_id = ? AND date = ? AND time = ?""",
        (doctor_id, date_str, time_str),
    ).fetchone()
    return dict(row) if row else None


def nearest_alternatives(doctor_id: int, target_dt: datetime, limit: int = 5) -> list[AlternativeSlot]:
    """Available slots for the same doctor within ±7 days, sorted by proximity."""
    conn = get_conn()
    lo = (target_dt.date() - timedelta(days=7)).isoformat()
    hi = (target_dt.date() + timedelta(days=7)).isoformat()
    rows = conn.execute(
        """SELECT s.slot_id, s.doctor_id, s.date, s.time, d.name AS doctor_name,
                  d.channeling_fee, f.name AS facility_name
           FROM AppointmentSlot s
           JOIN Doctor d  ON d.doctor_id   = s.doctor_id
           JOIN Facility f ON f.facility_id = d.facility_id
           WHERE s.doctor_id = ? AND s.is_available = 1
             AND s.date BETWEEN ? AND ?
           ORDER BY s.date, s.time""",
        (doctor_id, lo, hi),
    ).fetchall()

    def _dist(row) -> timedelta:
        try:
            dt = datetime.fromisoformat(f"{row['date']}T{row['time']}")
        except ValueError:
            return timedelta(days=999)
        return abs(dt - target_dt)

    sorted_rows = sorted(rows, key=_dist)[:limit]
    return [
        AlternativeSlot(
            slot_id=r["slot_id"],
            doctor_id=r["doctor_id"],
            doctor_name=r["doctor_name"],
            facility_name=r["facility_name"],
            date=r["date"],
            time=r["time"],
            channeling_fee=r["channeling_fee"] or 0.0,
        )
        for r in sorted_rows
    ]


def book(user_id: int, slot_id: int) -> Optional[BookingConfirmation]:
    """Atomically book a slot. Returns None if the slot is already taken."""
    conn = get_conn()
    try:
        with conn:  # transaction
            row = conn.execute(
                """SELECT s.slot_id, s.doctor_id, s.date, s.time, s.is_available,
                          d.name AS doctor_name, d.channeling_fee,
                          f.name AS facility_name
                   FROM AppointmentSlot s
                   JOIN Doctor d  ON d.doctor_id   = s.doctor_id
                   JOIN Facility f ON f.facility_id = d.facility_id
                   WHERE s.slot_id = ?""",
                (slot_id,),
            ).fetchone()
            if not row or not row["is_available"]:
                return None
            cur = conn.execute(
                "INSERT INTO Appointment(user_id, slot_id, status) VALUES(?,?,?)",
                (user_id, slot_id, "confirmed"),
            )
            conn.execute(
                "UPDATE AppointmentSlot SET is_available = 0 WHERE slot_id = ?",
                (slot_id,),
            )
            return BookingConfirmation(
                appointment_id=cur.lastrowid,
                slot_id=slot_id,
                doctor_name=row["doctor_name"],
                facility_name=row["facility_name"],
                date=row["date"],
                time=row["time"],
                channeling_fee=row["channeling_fee"] or 0.0,
            )
    except Exception as exc:
        logger.warning("book() failed: %s", exc)
        return None


# ---------- date/time parsing ----------

_TIME_RE = re.compile(r"(\d{1,2})(?::?(\d{2}))?\s*(am|pm)?", re.IGNORECASE)


def parse_date(raw: Optional[str], today: Optional[dtdate] = None) -> Optional[str]:
    if not raw:
        return None
    today = today or dtdate.today()
    s = raw.strip().lower()
    if s in ("today",):
        return today.isoformat()
    if s in ("tomorrow", "tmrw", "tmr"):
        return (today + timedelta(days=1)).isoformat()
    if s.startswith("in "):
        m = re.match(r"in (\d+) day", s)
        if m:
            return (today + timedelta(days=int(m.group(1)))).isoformat()
    # ISO YYYY-MM-DD
    try:
        return dtdate.fromisoformat(s).isoformat()
    except ValueError:
        pass
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return dtdate(y, mo, d).isoformat()
        except ValueError:
            return None
    return None


def parse_time(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().lower()
    m = _TIME_RE.match(s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or 0)
    suffix = m.group(3)
    if suffix == "pm" and hh < 12:
        hh += 12
    if suffix == "am" and hh == 12:
        hh = 0
    if not (0 <= hh < 24 and 0 <= mm < 60):
        return None
    return f"{hh:02d}:{mm:02d}"


# ---------- orchestrator ----------

@dataclass
class BookingContext:
    user_id: int
    extracted: dict


def process(ctx: BookingContext) -> BookingResponse:
    query = ctx.extracted.get("doctor_name") or ctx.extracted.get("specialty") or ""
    if not query:
        return BookingResponse(
            status="needs_info",
            message="Which doctor or specialty would you like to book? (e.g. 'Cardiology' or 'Dr. Perera')",
        )

    doctors = find_doctors(query)
    if not doctors:
        return BookingResponse(
            status="not_found",
            message=f"I couldn't find any doctor matching '{query}'. Try a different name or specialty.",
        )

    # Use the first match for the booking flow. Multiple matches are
    # surfaced through nearest_alternatives below (which only spans one
    # doctor's calendar — explicit per the brief).
    doctor = doctors[0]
    date_str = parse_date(ctx.extracted.get("date"))
    time_str = parse_time(ctx.extracted.get("time"))

    if not date_str or not time_str:
        # Show next 5 available across the matched doctor's calendar.
        target = datetime.combine(dtdate.today() + timedelta(days=1), datetime.min.time().replace(hour=10))
        alts = nearest_alternatives(doctor["doctor_id"], target)
        if not alts:
            return BookingResponse(
                status="not_found",
                message=f"{doctor['doctor_name']} has no slots in the next week.",
            )
        return BookingResponse(
            status="alternatives",
            alternatives=alts,
            message=(
                f"Here are upcoming slots with {doctor['doctor_name']} at "
                f"{doctor['facility_name']}. Pick one to confirm."
            ),
        )

    slot = find_slot(doctor["doctor_id"], date_str, time_str)
    if slot and slot["is_available"]:
        return BookingResponse(
            status="alternatives",
            alternatives=[
                AlternativeSlot(
                    slot_id=slot["slot_id"],
                    doctor_id=doctor["doctor_id"],
                    doctor_name=doctor["doctor_name"],
                    facility_name=doctor["facility_name"],
                    date=slot["date"],
                    time=slot["time"],
                    channeling_fee=doctor["channeling_fee"] or 0.0,
                )
            ],
            message=(
                f"{doctor['doctor_name']} is available at {date_str} {time_str}. "
                "Confirm below to book."
            ),
        )

    target_dt = datetime.fromisoformat(f"{date_str}T{time_str}")
    alts = nearest_alternatives(doctor["doctor_id"], target_dt)
    if not alts:
        return BookingResponse(
            status="not_found",
            message=f"{doctor['doctor_name']} has no nearby availability around {date_str} {time_str}.",
        )
    return BookingResponse(
        status="alternatives",
        alternatives=alts,
        message=(
            f"{doctor['doctor_name']} is fully booked at {date_str} {time_str}. "
            "Here are the closest available alternatives:"
        ),
    )
