"""Booking smoke tests — deterministic fallback, parsing, atomic book() (offline)."""

from __future__ import annotations

import datetime

from project.agents import booking_agent as b


def test_parse_time_and_date():
    assert b.parse_time("2pm") == "14:00"
    assert b.parse_time("09:30") == "09:30"
    assert b.parse_date("tomorrow", today=datetime.date(2026, 1, 1)) == "2026-01-02"


def test_process_returns_alternatives(seeded_db, no_api_key):
    resp = b.process(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    assert resp.status == "alternatives"
    assert len(resp.alternatives) >= 1


def test_process_agentic_falls_back_offline(seeded_db, no_api_key):
    # No API key → process_agentic must transparently use deterministic process().
    resp = b.process_agentic(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    assert resp.status == "alternatives"
    assert b._get_booking_agent() is None


def test_book_is_atomic_no_double_book(seeded_db, no_api_key):
    resp = b.process(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    slot_id = resp.alternatives[0].slot_id
    first = b.book(user_id=1, slot_id=slot_id)
    second = b.book(user_id=1, slot_id=slot_id)
    assert first is not None
    assert second is None  # slot already taken → no double-book


def test_cancel_frees_slot_and_blocks_others(seeded_db, no_api_key):
    resp = b.process(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    slot_id = resp.alternatives[0].slot_id
    booked = b.book(user_id=1, slot_id=slot_id)
    assert booked is not None

    # Another user cannot cancel this appointment.
    assert b.cancel(user_id=999, appointment_id=booked.appointment_id) is None

    cancelled = b.cancel(user_id=1, appointment_id=booked.appointment_id)
    assert cancelled is not None
    assert cancelled.appointment_id == booked.appointment_id

    rows = b.list_appointments(1, include_cancelled=True)
    match = next(r for r in rows if r["appointment_id"] == booked.appointment_id)
    assert match["status"] == "cancelled"
    assert match["is_available"] == 1

    # Slot can be booked again after cancel.
    again = b.book(user_id=1, slot_id=slot_id)
    assert again is not None


def test_cancel_idempotent_second_call_fails(seeded_db, no_api_key):
    resp = b.process(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    booked = b.book(user_id=1, slot_id=resp.alternatives[0].slot_id)
    assert b.cancel(user_id=1, appointment_id=booked.appointment_id) is not None
    assert b.cancel(user_id=1, appointment_id=booked.appointment_id) is None


def test_reschedule_frees_old_and_books_new(seeded_db, no_api_key):
    resp = b.process(b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"}))
    assert len(resp.alternatives) >= 2
    first_slot = resp.alternatives[0].slot_id
    second_slot = resp.alternatives[1].slot_id
    booked = b.book(user_id=1, slot_id=first_slot)
    assert booked is not None

    # Other user cannot reschedule.
    assert b.reschedule(999, booked.appointment_id, second_slot) is None

    moved = b.reschedule(1, booked.appointment_id, second_slot)
    assert moved is not None
    assert moved.slot_id == second_slot

    old = seeded_db.get_conn().execute(
        "SELECT status FROM Appointment WHERE appointment_id = ?",
        (booked.appointment_id,),
    ).fetchone()
    assert old["status"] == "cancelled"
    avail = seeded_db.get_conn().execute(
        "SELECT is_available FROM AppointmentSlot WHERE slot_id = ?",
        (first_slot,),
    ).fetchone()["is_available"]
    assert avail == 1
    new_avail = seeded_db.get_conn().execute(
        "SELECT is_available FROM AppointmentSlot WHERE slot_id = ?",
        (second_slot,),
    ).fetchone()["is_available"]
    assert new_avail == 0


def test_parse_date_weekday_phrase():
    # Step 5: "next <weekday>" resolves to the next future occurrence (Sun 2026-06-21).
    today = datetime.date(2026, 6, 21)
    assert b.parse_date("next tuesday", today=today) == "2026-06-23"
    assert b.parse_date("friday", today=today) == "2026-06-26"


def test_agent_prompt_includes_raw_text():
    # Step 5: the verbatim request must reach the LLM prompt.
    ctx = b.BookingContext(user_id=1, extracted={"specialty": "Cardiology"},
                           raw_text="book me a heart doctor next tuesday")
    prompt = b._agent_prompt(ctx)
    assert "Cardiology" in prompt
    assert "book me a heart doctor next tuesday" in prompt


def test_booking_agent_builds_with_key(monkeypatch):
    # Proves the Step 3 fix stays fixed: with a key + pydantic-ai present, the agent
    # actually BUILDS (module-level RunContext import resolves @agent.tool hints).
    # Build only — run_sync is never called, so there is no network.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-build-only")
    b._booking_agent = None
    try:
        assert b._PYDANTIC_AI_AVAILABLE
        assert b._get_booking_agent() is not None
    finally:
        b._booking_agent = None  # reset so the offline tests still observe None
