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
