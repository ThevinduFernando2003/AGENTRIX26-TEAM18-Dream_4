"""Hospital staff services — bookings, no-show, slot templates (Phase 1 / FR-H03).

No LLM involvement. All writes go through typed SQL helpers.
"""

from __future__ import annotations

from datetime import date as dtdate, timedelta
from typing import Optional

from . import authz
from .db.repo import connection as get_conn


def todays_bookings(account: dict, *, day: Optional[str] = None) -> list[dict]:
    """Confirmed appointments for doctors at the staff facility on ``day`` (default today)."""
    if not authz.is_hospital_staff(account) or not account.get("facility_id"):
        return []
    day = day or dtdate.today().isoformat()
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.appointment_id, a.status, a.booked_at,
                  s.slot_id, s.date, s.time,
                  d.doctor_id, d.name AS doctor_name,
                  u.user_id AS patient_id, u.full_name AS patient_name, u.username AS patient_username
           FROM Appointment a
           JOIN AppointmentSlot s ON s.slot_id = a.slot_id
           JOIN Doctor d ON d.doctor_id = s.doctor_id
           JOIN User u ON u.user_id = a.user_id
           WHERE d.facility_id = ? AND s.date = ? AND a.status IN ('confirmed', 'no_show')
           ORDER BY s.time, a.appointment_id""",
        (account["facility_id"], day),
    ).fetchall()
    return [dict(r) for r in rows]


def mark_no_show(account: dict, appointment_id: int) -> bool:
    """Mark a confirmed appointment as no_show. Does not free the slot (attendance event)."""
    if not authz.is_hospital_staff(account) or not account.get("facility_id"):
        return False
    conn = get_conn()
    row = conn.execute(
        """SELECT a.appointment_id, a.status, d.facility_id
           FROM Appointment a
           JOIN AppointmentSlot s ON s.slot_id = a.slot_id
           JOIN Doctor d ON d.doctor_id = s.doctor_id
           WHERE a.appointment_id = ?""",
        (appointment_id,),
    ).fetchone()
    if not row or row["status"] != "confirmed":
        return False
    if not authz.can_manage_facility(account, row["facility_id"]):
        return False
    with conn:
        conn.execute(
            "UPDATE Appointment SET status = 'no_show' WHERE appointment_id = ?",
            (appointment_id,),
        )
    return True


def publish_slot_template(
    account: dict,
    doctor_id: int,
    *,
    weekdays: list[int],
    times: list[str],
    days_ahead: int = 14,
    start: Optional[dtdate] = None,
) -> int:
    """Publish available slots for ``doctor_id`` on matching weekdays for ``days_ahead`` days.

    ``weekdays`` uses Monday=0 … Sunday=6 (``date.weekday()``).
    Returns number of new slots inserted. Skips duplicates.
    """
    if not authz.can_publish_slot(account, doctor_id):
        return 0
    if days_ahead < 0 or days_ahead > 90:
        return 0
    start = start or dtdate.today()
    wanted = {int(w) for w in weekdays if 0 <= int(w) <= 6}
    clean_times = sorted({t.strip() for t in times if t and ":" in t})
    if not wanted or not clean_times:
        return 0

    conn = get_conn()
    created = 0
    with conn:
        for offset in range(days_ahead + 1):
            day = start + timedelta(days=offset)
            if day.weekday() not in wanted:
                continue
            day_s = day.isoformat()
            for time_hm in clean_times:
                exists = conn.execute(
                    """SELECT 1 FROM AppointmentSlot
                       WHERE doctor_id = ? AND date = ? AND time = ?""",
                    (doctor_id, day_s, time_hm),
                ).fetchone()
                if exists:
                    continue
                conn.execute(
                    """INSERT INTO AppointmentSlot(doctor_id, date, time, is_available)
                       VALUES(?,?,?,1)""",
                    (doctor_id, day_s, time_hm),
                )
                created += 1
    return created
