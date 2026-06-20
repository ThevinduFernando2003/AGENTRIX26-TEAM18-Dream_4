# Pydantic AI Booking Agent Design - Phase 2

**Owner:** Thevindu  
**Phase:** 2 (Phase 1 design doc only, implementation in Phase 2)  
**Status:** Design specification (no code yet)

## Overview

This document specifies the design of a **Pydantic AI agent** for the doctor appointment booking flow. In **Phase 1**, the existing deterministic `process()` function in `booking_agent.py` remains the fallback. In **Phase 2**, we implement this agent alongside the fallback, using Gemini free-tier API.

## Goals

1. **Typed automation:** Replace fuzzy string matching with a structured LLM agent that extracts booking intent, resolves ambiguous doctor/specialty names, and suggests alternatives.
2. **Grounded results:** Leverage Janidu's `retrieve()` function (RAG) to ground specialty and facility suggestions in actual DB data.
3. **Atomicity:** Maintain atomic `book()` operation — no double-booking even under concurrent requests.
4. **Offline fallback:** When `GEMINI_API_KEY` is absent, the deterministic `process()` path runs instead.

---

## Architecture

### Agent Structure

```
BookingAgent (pydantic_ai.Agent)
  ├── Model: Gemini (gemini-1.5-flash free tier, configurable)
  ├── System prompt: instructs the agent on booking rules, DB structure
  ├── Tools:
  │   ├── find_doctors(specialty: str, facility: str | None) -> list[Doctor]
  │   ├── find_slot(doctor_id: int, date_range: DateRange, time_pref: str | None) -> list[Slot]
  │   ├── nearest_alternatives(doctor_id: int, date: str, slot_count: int) -> list[Slot]
  │   └── book_slot(user_id: int, slot_id: int) -> BookingConfirmation | None
  │
  └── Output schema: BookingResponse (Pydantic model)
      - status: "booked" | "alternatives" | "not_found" | "needs_info"
      - confirmation: BookingConfirmation (if booked)
      - alternatives: list[AlternativeSlot]
      - message: str
```

### Execution Flow

```
User message (chat/UI)
  ↓
Extract BookingRequest (intent detection in chatbot or form)
  ↓
Check: does user intent look like booking?
  (If yes, route to booking flow)
  ↓
Invoke BookingAgent.run_booking(request)
  ├─ [Phase 1 → fallback to deterministic process()]
  └─ [Phase 2 → if GEMINI_API_KEY, run agent; else fallback]
  ↓
BookingAgent orchestrates:
  1. Call find_doctors(specialty, facility) 
  2. Resolve to actual doctor(s) or ask for clarification
  3. Call find_slot(doctor_id, date_range, time_pref)
  4. If exact match found, call book_slot() immediately
  5. Else, call nearest_alternatives() and return suggestions
  ↓
Return BookingResponse to UI panel
  ├─ If status="booked" → show confirmation
  ├─ If status="alternatives" → show list + buttons (existing panel logic)
  └─ Else → show error or "needs more info"
```

---

## Tool Specifications

### 1. `find_doctors(specialty: str, facility: str | None = None) -> list[Doctor]`

**Purpose:** Resolve specialty (possibly fuzzy) to actual doctor(s) via RAG or DB query.

**Parameters:**
- `specialty` (str): specialty name, possibly fuzzy (e.g., "heart doctor", "cardio", "cardiology")
- `facility` (str | None): optional facility filter (e.g., "colombo central", "nuwara eliya")

**Returns:** `list[Doctor]`
```python
class Doctor(BaseModel):
    doctor_id: int
    name: str
    specialty: str  # real DB specialty
    facility_id: int
    facility_name: str
```

**Implementation notes:**
- Use Janidu's `retrieve(query, collection="specialties", k=5)` to find matching specialties.
- Query DB for doctors in those specialties.
- If facility is specified, filter by facility_id.
- If no match, return `[]`.

### 2. `find_slot(doctor_id: int, date_range: str, time_pref: str | None = None) -> list[Slot]`

**Purpose:** Find available appointment slots for a specific doctor.

**Parameters:**
- `doctor_id` (int): doctor ID
- `date_range` (str): e.g., "tomorrow", "next week", "2026-06-25 to 2026-07-02", "any"
- `time_pref` (str | None): optional time preference (e.g., "morning", "afternoon", "10:00")

**Returns:** `list[Slot]` (empty if no slots available)
```python
class Slot(BaseModel):
    slot_id: int
    doctor_id: int
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    channeling_fee: float
    available: bool
```

**Implementation notes:**
- Parse date_range using `parse_date_range()` (helper in Phase 2).
- Query `AppointmentSlot` table with `available=true` and date in range.
- Sort by date, then time.
- If time_pref is given, prioritize matching times (e.g., "morning" = 06:00–12:00).

### 3. `nearest_alternatives(doctor_id: int, date: str, slot_count: int = 3) -> list[Slot]`

**Purpose:** When the requested doctor/date is not available, suggest up to `slot_count` alternatives nearby (same specialty, close date/time, nearby facilities).

**Parameters:**
- `doctor_id` (int): the originally requested doctor
- `date` (str): originally requested date (YYYY-MM-DD)
- `slot_count` (int): max alternatives to return (default 3)

**Returns:** `list[Slot]` (sorted by relevance: closest date, then closest doctor facility)

**Implementation notes:**
- Query the database for:
  - Same specialty, different doctors
  - Dates within ±7 days of requested date
  - Facilities sorted by distance to user's location (if available)
- Score by `(days_diff, facility_distance)` and return top `slot_count`.

### 4. `book_slot(user_id: int, slot_id: int) -> BookingConfirmation | None`

**Purpose:** Atomically book a slot and return confirmation or None if slot was taken.

**Parameters:**
- `user_id` (int): user ID
- `slot_id` (int): slot ID to book

**Returns:** `BookingConfirmation | None`
- If successful, return confirmation with appointment_id.
- If slot already booked, return None.

**Implementation notes:**
- Use database **transaction with isolation level SERIALIZABLE** or **row-level lock**:
  1. Check if slot is still available.
  2. If available, insert into `Appointment` table.
  3. Mark `AppointmentSlot.available = false`.
  4. Commit.
- If any conflict (slot taken or user already has overlapping appointment), rollback and return None.

---

## Phases of Implementation

### Phase 1 (Current)
- ✅ Define tool specifications (this document).
- ✅ Refactor existing deterministic `process()` to be the fallback path.
- Define `BookingRequest` and `BookingResponse` schemas (already done in `models/booking.py`).
- Plan remediation for reminder-vs-booking collision (see below).

### Phase 2
- Implement `BookingAgent` class with pydantic_ai.
- Wire tools to DB (implement find_doctors, find_slot, nearest_alternatives, book_slot).
- Integrate RAG: use `retrieve()` for fuzzy specialty matching.
- Add date/time parsing utilities.
- Smoke test offline fallback (GEMINI_API_KEY unset).

---

## Reminder-vs-Booking Intent Collision (Phase 1 Fix)

### Problem

Currently in `basic_chatbot.py`:
```python
if detect_reminder(reply_text):  # Regex-based, runs first
    # Mark as reminder
    route = "reminders"
else:
    # Continue to router
```

When user says *"Book me an appointment in 2 weeks"* or *"I need to come back for a follow-up in 2 weeks"*:
- `detect_reminder()` fires because of "in 2 weeks" → sets route="reminders"
- Booking agent never sees the request

### Solution (Phase 1)

Add a **pre-filter** in the router or booking agent:
```python
def should_route_to_booking(user_input: str) -> bool:
    """
    Return True if user intent clearly includes booking verbs.
    Booking verbs: "book", "appointment", "schedule", "book an appointment", etc.
    """
    booking_verbs = ["book", "appointment", "schedule", "slot", "doctor", "reserve"]
    user_lower = user_input.lower()
    return any(verb in user_lower for verb in booking_verbs)

def detect_reminder(text: str) -> bool:
    """
    Return True only if the text is about a future visit but has NO booking verbs.
    """
    reminder_patterns = [
        r"\b(?:come back|follow.?up|visit again|checkup|revisit|call|comeback)\b.*\b(?:in|on|after)\s+(?:\d+\s+)?(?:week|day|month|year)",
    ]
    reminder_match = any(re.search(p, text, re.IGNORECASE) for p in reminder_patterns)
    booking_match = should_route_to_booking(text)
    # Only treat as reminder if we found reminder pattern AND NO booking verbs
    return reminder_match and not booking_match
```

### Implementation Location

- **Phase 1:** Add `should_route_to_booking()` check in `basic_chatbot.py` or in the routing logic.
- **Phase 2:** May refine via the Pydantic AI agent's system prompt.

---

## Dependencies & Configuration

### Gemini Free-Tier Setup
- Model: `gemini-1.5-flash`
- Embeddings: (used by Janidu's RAG in Phase 2) `text-embedding-004`
- Key env var: `GEMINI_API_KEY` (standard; handled by Chanupa in `.env`)

### Database Schema Requirements
- `Doctor` table: id, name, specialty, facility_id, …
- `Facility` table: id, name, address, lat, lng, …
- `AppointmentSlot` table: id, doctor_id, date, time, available, channeling_fee, …
- `Appointment` table: id, user_id, slot_id, booked_at, …

### Libraries
- `pydantic-ai>=0.4.3` (already installed)
- `python-dateutil` (for parsing date ranges)

---

## Testing Strategy (Phase 3)

- Unit tests for each tool (find_doctors, find_slot, etc.) with a temp SQLite DB.
- Integration tests: agent runs through a booking request end-to-end.
- Offline fallback test: agent gracefully falls back when `GEMINI_API_KEY` is missing.
- Concurrency test: two users booking the same slot simultaneously (only one succeeds).

---

## Summary

The Pydantic AI booking agent will transform the booking flow from rule-based / fuzzy-matching to a structured, grounded, LLM-orchestrated process. Phase 1 establishes the design and fixes immediate collisions. Phase 2 implements the agent itself. Phase 3 validates end-to-end correctness and concurrency safety.
