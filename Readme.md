# MedBridge AI

**Multi-agent healthcare navigator for Sri Lanka — AgenTrix 2026 · Team Dream_4 (TEAM18)**

MedBridge AI is a Streamlit-based conversational assistant that helps patients triage symptoms, book doctor appointments, compare medicine prices across pharmacies, and get independent specialist reviews of medical reports — all without ever producing a diagnosis. Every AI-generated response carries an explicit disclaimer and the system is designed to degrade gracefully when API keys are unavailable.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [Building the RAG Index](#building-the-rag-index)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [Seed / Demo Data](#seed--demo-data)
- [Demo Walkthrough](#demo-walkthrough)
- [Team & Ownership](#team--ownership)
- [Technical Constraints](#technical-constraints)

---

## Features

### Tier 1 — Core
| Feature | Description |
|---|---|
| **Authentication** | Signup / login with bcrypt-hashed passwords. Session persists across browser refresh. |
| **Multi-session chat** | Claude/ChatGPT-style sidebar history — new chat, switch sessions, delete sessions. |
| **Emergency screener** | Pure-regex screener runs *before* every LLM call. Matches 30+ patterns across English, Sinhala (romanised) and Tamil (romanised). Confirmed emergencies show a `tel:1990` Suwa Seriya link and push a family alert via ntfy.sh. |
| **Triage chatbot** | CrewAI + Gemini orchestrator. Classifies intent (booking / medicine / report / general), drafts a warm reply, persists full history. Deterministic keyword fallback when no API key is present. |
| **Booking agent** | Pydantic AI typed-output agent. Resolves doctor/specialty via RAG, finds slots, returns 3–5 nearby alternatives when the requested slot is full, books atomically with a DB transaction, and sends a confirmation push via ntfy.sh. |
| **Medicine tracker** | Text-input pharmacy price/distance comparison. Fuzzy + RAG name matching (edit-distance precision guard prevents false positives). Shows items, totals, distance from the user's location and out-of-stock indicators. |
| **Persistent history** | All chat turns are stored in SQLite per user and per session. |

### Tier 2 — Specialist Panel
| Feature | Description |
|---|---|
| **Specialist Panel** | Three independent CrewAI agents (cardiology, internal medicine, radiology) read the same report text in parallel threads with no shared state. Each builds its own `LLM`/`Agent`/`Crew`. |
| **Moderator agent** | Synthesises the three opinions into a `ConsensusReport`. `points_of_disagreement` is structurally guaranteed non-empty — a code-level guard in `moderator.py` injects "No material disagreement" rather than silently returning an empty list. |
| **Prescription OCR** | Gemini Vision transcribes an uploaded prescription photo. The user must confirm (and may edit) the transcription before any pharmacy lookup runs. Falls back to a text-paste path when `GEMINI_API_KEY` is absent. |
| **ntfy.sh notifications** | Four notification types: `emergency`, `booking_confirmed`, `report_review_complete`, `prescription_confirmed`. All logged to `NotificationLog`. |

### Tier 3 — Internationalisation & Voice
| Feature | Description |
|---|---|
| **Trilingual UI** | Full English / Sinhala / Tamil via a static i18n catalog (`project/i18n/translate.py`). Language switcher in the sidebar persists to the database. |
| **Dynamic translation** | Free-form agent replies are translated through Gemini when the user prefers Sinhala or Tamil. Cached per process. Returns English unchanged when no API key is set. |
| **Voice input** | Gemini `gemini-2.5-flash` speech-to-text via `st.audio_input`. Disabled gracefully when `GEMINI_API_KEY` is absent. |
| **Voice output** | gTTS (free, no API key) generates an MP3 of each assistant reply when the sidebar toggle is on. |
| **Future-visit reminders** | Regex detector inside the chatbot detects natural-language follow-up mentions ("come back in 2 weeks", "next month", specific ISO dates), persists a `FutureVisitReminder` row, and fires ntfy pushes on demand from the sidebar. |

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Streamlit UI (app.py)               │
│  ┌──────────┐  ┌────────┐  ┌────────────────────┐   │
│  │ sidebar  │  │  chat  │  │  domain panels      │   │
│  │ sessions │  │ router │  │  booking / medicine │   │
│  │ language │  │ voice  │  │  report / rx / em   │   │
│  └──────────┘  └───┬────┘  └────────────────────┘   │
└───────────────────┬┘────────────────────────────────┘
                    │ route_request signal
        ┌───────────▼───────────────────────────┐
        │           Agent layer                 │
        │  basic_chatbot (CrewAI orchestrator)  │
        │  booking_agent  (Pydantic AI)         │
        │  medicine_tracker                     │
        │  specialist_panel (3× parallel CrewAI)│
        │  moderator       (consensus + guard)  │
        │  emergency       (pure regex)         │
        │  reminders       (rule-based)         │
        │  vision_ocr      (Gemini Vision)      │
        └───────────┬───────────────────────────┘
                    │
        ┌───────────▼───────────────────────────┐
        │             RAG layer                 │
        │  ChromaDB  ←  ingest.py               │
        │  embeddings: local ONNX / Gemini      │
        │  collections: symptoms, facilities,   │
        │               medicines               │
        └───────────┬───────────────────────────┘
                    │
        ┌───────────▼───────────────────────────┐
        │          SQLite (project/db/app.db)   │
        │  17 tables — User, ChatMessage,       │
        │  ChatSession, Appointment, Medicine,  │
        │  Pharmacy, MedicalReport, …           │
        └───────────────────────────────────────┘
```

**Key design decisions:**
- `app.py` is a thin shell — all UI logic lives in `project/ui/panels/`. Each panel owns one domain and communicates with others only through `st.session_state` signals.
- The RAG layer is offline-safe: `retrieve()` always returns `[]` (never raises) when the index has not been built yet, so every agent falls back to its deterministic heuristic.
- Emergency screening runs synchronously *before* any LLM call. No network latency on the critical safety path.
- Passwords are hashed with `passlib[bcrypt]`. Never stored in plaintext, including seed users.

---

## Project Structure

```
AGENTRIX26-TEAM18-Dream_4/
├── Readme.md
├── pyproject.toml              # build, lint (ruff), format (black), pytest config
├── requirements-dev.txt        # dev/CI deps (pytest, ruff, black)
│
├── docs/
│   ├── rag.md                  # RAG subsystem technical reference
│   └── BOOKING_AGENT_DESIGN.md # Pydantic AI booking agent design spec
│
├── tests/
│   ├── conftest.py             # shared fixtures: seeded_db, chroma_tmp, no_api_key
│   ├── test_booking.py
│   ├── test_medicine.py
│   └── test_rag.py
│
└── project/
    ├── requirements.txt
    ├── __init__.py
    │
    ├── agents/
    │   ├── basic_chatbot.py    # CrewAI orchestrator, chat sessions, reminder detection
    │   ├── booking_agent.py    # Pydantic AI typed booking + RAG-grounded doctor lookup
    │   ├── emergency.py        # Pure-regex screener (no LLM, no network)
    │   ├── medicine_tracker.py # Pharmacy comparison, RAG fuzzy matching, OCR confirm
    │   ├── moderator.py        # Consensus synthesis + disagreement guard
    │   ├── reminders.py        # Future-visit reminder service + ntfy push
    │   ├── specialist_panel.py # 3 parallel independent CrewAI specialists
    │   └── vision_ocr.py       # Gemini Vision prescription transcription
    │
    ├── db/
    │   ├── schema.sql          # 17-table SQLite schema (idempotent CREATE IF NOT EXISTS)
    │   ├── db.py               # get_conn(), init_db(), schema migration
    │   └── seed.py             # Idempotent seed loader (hashes passwords on insert)
    │
    ├── i18n/
    │   ├── translate.py        # Static i18n catalog (EN/SI/TA) + Gemini dynamic translation
    │   ├── tts.py              # gTTS wrapper (free, no API key)
    │   └── stt.py              # Gemini speech-to-text wrapper
    │
    ├── kb/
    │   ├── rag_knowledge/      # Hand-curated JSONs ingested into Chroma
    │   │   └── symptom_specialty.json
    │   ├── sample_reports/     # Demo medical report text files
    │   ├── seed_facilities.json
    │   ├── seed_medicines.json
    │   ├── seed_pharmacy_prices.json
    │   └── seed_users.json
    │
    ├── models/
    │   ├── __init__.py         # Re-exports all models (backward compat)
    │   ├── common.py           # Shared types: INTENT, SPECIALIST
    │   ├── booking.py          # BookingRequest, AlternativeSlot, BookingConfirmation, BookingResponse
    │   ├── chat.py             # ChatTurn, EmergencyDecision, RouterOutput
    │   ├── medicine.py         # MedicineQuery, PharmacyQuote, MedicineQuoteResult, OcrConfirmation
    │   └── panel.py            # SpecialistOpinion, ConsensusReport, PanelResult
    │
    ├── notifications/
    │   └── ntfy_client.py      # HTTP POST to ntfy.sh + NotificationLog
    │
    ├── rag/
    │   ├── __init__.py         # Re-exports retrieve()
    │   ├── embeddings.py       # Local ONNX / Gemini embedding function
    │   ├── ingest.py           # Build Chroma index from KB (run once)
    │   └── retriever.py        # retrieve(query, collection, k) — always offline-safe
    │
    └── ui/
        ├── app.py              # Streamlit entry point (thin shell)
        ├── auth.py             # bcrypt login/signup/logout, language update
        ├── common.py           # Shared helpers: get_geo, lang_of, banners
        └── panels/
            ├── __init__.py     # Panel contract documentation
            ├── booking.py      # Booking suggestions + slot confirmation
            ├── chat.py         # Chat history, voice input, intent router
            ├── emergency.py    # Emergency panel (confirm → tel:1990 + ntfy)
            ├── medicine.py     # Pharmacy comparison table
            ├── prescription.py # OCR upload + user confirmation gate
            ├── report.py       # Specialist panel UI
            └── sidebar.py      # Sessions, language, location, reminders, logout
```

---

## Database Schema

The SQLite database (`project/db/app.db`) has 17 tables:

| Table | Purpose |
|---|---|
| `User` | Accounts with bcrypt-hashed passwords, preferred language, family contact |
| `ChatSession` | Named conversation sessions per user |
| `ChatMessage` | Individual chat turns linked to a session |
| `MedicalReport` | Uploaded/pasted report text |
| `SpecialistOpinion` | One row per specialist per report |
| `ConsensusReport` | Moderator synthesis |
| `Specialty` | Doctor specialties |
| `Facility` | Hospitals and clinics with coordinates |
| `Doctor` | Doctors linked to facility and specialty |
| `AppointmentSlot` | Available booking slots |
| `Appointment` | Confirmed bookings |
| `FutureVisitReminder` | Reminder rows with target date/month |
| `Prescription` | OCR'd prescription text with user confirmation flag |
| `Medicine` | Medicine catalog with reference dosage text |
| `Pharmacy` | Pharmacies with coordinates |
| `PharmacyMedicinePrice` | Per-pharmacy medicine prices and stock |
| `NotificationLog` | Audit log of every ntfy.sh push attempt |

---

## Setup & Installation

**Requirements:** Python 3.11+

```bash
# 1. Clone the repository
git clone https://github.com/Agentrix-ComES/AGENTRIX26-TEAM18-Dream_4.git
cd AGENTRIX26-TEAM18-Dream_4

# 2. Create a virtual environment
python -m venv project/venv
source project/venv/bin/activate      # Windows: project\venv\Scripts\activate

# 3. Install runtime dependencies
pip install -r project/requirements.txt

# 4. Configure environment variables
cp project/.env.example project/.env
# Edit project/.env and set GEMINI_API_KEY (free tier is sufficient)

# 5. Initialise the database and load seed data
python -m project.db.db

# 6. (Optional) Build the RAG index
python -m project.rag.ingest
```

> **Without `GEMINI_API_KEY`:** The chatbot falls back to a deterministic keyword router, voice input and output are disabled, and the specialist panel returns deterministic stub opinions. The booking, medicine, and emergency flows work fully without an API key.

---

## Running the App

```bash
streamlit run project/ui/app.py
```

The app will open at `http://localhost:8501`.

---

## Building the RAG Index

The RAG index powers grounded symptom→specialty routing, doctor/facility lookup, and medicine name matching. Build it once after installation (and after any knowledge-base edits):

```bash
python -m project.rag.ingest
```

By default this uses a local ONNX embedding model (no API key required). To use Gemini embeddings instead:

```bash
RAG_EMBED_BACKEND=gemini python -m project.rag.ingest
```

The index is persisted to `project/rag/chroma/` and is reused on subsequent runs. Repeated `ingest` calls are idempotent (upsert by content hash).

---

## Running Tests

```bash
# Install dev dependencies first
pip install -r requirements-dev.txt

# Run the full test suite (offline — no API key required)
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_booking.py -v
```

All tests run fully offline. The `seeded_db` fixture redirects the database to a temporary file. The `chroma_tmp` fixture builds a throwaway Chroma index using local ONNX embeddings.

---

## Environment Variables

Configure these in `project/.env`:

| Variable | Default | Required | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | — | Optional | Gemini free-tier key for chatbot, translation, voice, OCR |
| `GEMINI_MODEL` | `gemini-2.5-flash` | No | Gemini model ID |
| `NTFY_TOPIC_PREFIX` | `medbridge-demo` | No | ntfy.sh topic prefix — per-user topic = `{prefix}-{user_id}` |
| `NTFY_BASE` | `https://ntfy.sh` | No | ntfy.sh base URL (self-hosted option) |
| `RAG_EMBED_BACKEND` | `local` | No | `local` (ONNX) or `gemini` for embeddings |

---

## Seed / Demo Data

All seed data is clearly labelled **SEED / MOCK** — it is not real clinical or commercial data.

Pre-seeded demo users:

| Username | Password | Language |
|---|---|---|
| `demo1` | `demo1pass` | English |
| `demo2` | `demo2pass` | English |
| `demo3` | `demo3pass` | Sinhala |
| `demo4` | `demo4pass` | Tamil |
| `demo5` | `demo5pass` | English |
| `demo6` | `demo6pass` | English |

Seed data includes: 5 facilities, 10+ doctors, 50+ appointment slots, 10 medicines, 5 pharmacies with pricing, and 3 medical report sample files.

---

## Demo Walkthrough

### Basic flow

1. Open `http://localhost:8501` — sign up with a new account or log in as `demo1 / demo1pass`.
2. In the sidebar, copy your ntfy topic and subscribe at `https://ntfy.sh/<topic>` in another tab (free, no signup).
3. Set your location using the 📍 geolocation button or enter coordinates manually (Colombo default: `6.9271, 79.8612`).

### Emergency detection
4. Type: `I have severe chest pain and can't breathe.`
   - Red emergency panel appears. Confirm → `tel:1990` button + ntfy push to family contact.

### Booking
5. Type: `Book me with Dr. Sunil Perera tomorrow at 10:00`
   - That slot is intentionally seeded as full. The agent returns 3–5 nearby alternatives. Click **Book** → confirmation + ntfy push.

### Medicine prices
6. Type: `I need prices for Panadol and Amoxicillin`
   - Sorted pharmacy comparison with totals and distance from your location.

### Specialist report review
7. Type: `Can you review my ECG report?`
   - The Specialist Panel expander opens. Pick `report_ambiguous_findings.txt`, click **Run Specialist Panel**.
   - Three columns show independent findings. Below them the Moderator lists agreements and disagreements.

### Prescription OCR
8. Open **💊 Prescription photo**, upload a JPG/PNG of a prescription.
   - Gemini Vision transcribes it. Confirm the text before any pharmacy lookup runs.

### Multilingual
9. Log in as `demo3 / demo3pass` (Sinhala) or `demo4 / demo4pass` (Tamil).
   - All sidebar labels, buttons, and panel text switch to the selected language.
   - Use the language radio (`E / සි / த`) in the sidebar to switch languages live.

### Reminders
10. Type: `Doctor asked me to come back in 2 weeks`
    - Reminder saved. Click **🔔 Check my reminders** in the sidebar to fire the ntfy push.

### Chat sessions
11. Click **✏️ New chat** in the sidebar to start a fresh conversation.
    - Past sessions are listed with auto-generated titles. Click any to reopen. Delete with 🗑.

---

## Team & Ownership

| Member | Domain |
|---|---|
| **Chanupa** | Auth (`ui/auth.py`), emergency panel, report panel, DB schema, specialist agents, moderator, notifications, `pyproject.toml`, requirements |
| **Thevindu** | Booking models (`models/booking.py`), booking panel (`ui/panels/booking.py`), reminder-vs-booking collision fix, UI corrections (banners, language switcher) |
| **Nisal** | Medicine models (`models/medicine.py`), medicine panel, prescription panel, i18n fixes |
| **Janidu** | RAG subsystem (`rag/`), chat panel (`ui/panels/chat.py`), emergency agent, `ui/app.py` routing |

File ownership is documented in `OWNERS.md`.

---

## Technical Constraints

- **Free-tier only** — Gemini free tier, ntfy.sh free topics. No paid APIs required.
- **No diagnosis** — The disclaimer is injected by the UI layer, never by the LLM, so it cannot be omitted by a malformed generation.
- **No plaintext passwords** — `passlib[bcrypt]` hashes all passwords including seed users.
- **No real data** — All facility, doctor, slot, pharmacy, and price data is clearly marked SEED/MOCK in the seed files and in the UI.
- **No n8n / Zapier** — All orchestration is real Python (CrewAI + Pydantic AI).
- **Emergency dialling** — Rendered as a `tel:1990` link (opens the device's native dialer). No paid telephony.
- **Medicine dosage** — The tracker never invents dosage text. Only `reference_dosage_text` from the seed catalog is displayed.
- **RAG offline-safe** — `retrieve()` returns `[]` and never raises when the index has not been built. All agents have deterministic fallbacks.

---

## License

© Dream 4. All rights reserved.
