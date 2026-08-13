"""Hospital portal services — today's bookings, no-show, slot templates."""

from __future__ import annotations

from datetime import date, timedelta

from project import hospital_service, supplier_auth
from project.agents import booking_agent as b


def test_todays_bookings_and_no_show(seeded_db, no_api_key):
    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    assert hospital is not None
    doc = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id = ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    day = (date.today() + timedelta(days=1)).isoformat()
    # Ensure an available slot tomorrow for this doctor.
    conn = seeded_db.get_conn()
    slot = conn.execute(
        """SELECT slot_id FROM AppointmentSlot
           WHERE doctor_id = ? AND date = ? AND is_available = 1 LIMIT 1""",
        (doc["doctor_id"], day),
    ).fetchone()
    if not slot:
        conn.execute(
            """INSERT INTO AppointmentSlot(doctor_id, date, time, is_available)
               VALUES(?,?,?,1)""",
            (doc["doctor_id"], day, "09:00"),
        )
        conn.commit()
        slot = conn.execute(
            """SELECT slot_id FROM AppointmentSlot
               WHERE doctor_id = ? AND date = ? AND time = '09:00'""",
            (doc["doctor_id"], day),
        ).fetchone()

    booked = b.book(user_id=1, slot_id=slot["slot_id"])
    assert booked is not None

    rows = hospital_service.todays_bookings(hospital, day=day)
    assert any(r["appointment_id"] == booked.appointment_id for r in rows)

    # Pharmacy staff cannot mark no-show at hospital.
    pharmacy = supplier_auth.login("union", "unionpass")
    assert hospital_service.mark_no_show(pharmacy, booked.appointment_id) is False

    assert hospital_service.mark_no_show(hospital, booked.appointment_id) is True
    status = conn.execute(
        "SELECT status FROM Appointment WHERE appointment_id = ?",
        (booked.appointment_id,),
    ).fetchone()["status"]
    assert status == "no_show"
    # Idempotent failure on second mark.
    assert hospital_service.mark_no_show(hospital, booked.appointment_id) is False


def test_slot_template_respects_facility(seeded_db):
    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    own = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id = ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    other = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id != ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    start = date.today() + timedelta(days=30)
    n_own = hospital_service.publish_slot_template(
        hospital,
        own["doctor_id"],
        weekdays=[start.weekday()],
        times=["08:00"],
        days_ahead=0,
        start=start,
    )
    assert n_own == 1
    n_other = hospital_service.publish_slot_template(
        hospital,
        other["doctor_id"],
        weekdays=[start.weekday()],
        times=["08:00"],
        days_ahead=0,
        start=start,
    )
    assert n_other == 0
