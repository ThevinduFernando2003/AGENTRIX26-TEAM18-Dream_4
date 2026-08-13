# MedBridge AI — Codebase Explanation & Path Map

**Local only — do not push.** Study sheet for viva / defense.  
**Branch context:** built on `viva-prep` work; local branch may be `booking`.  
**Root:** `d:\Dev\Competitions\Agentrix\MedBridge-AI`

---

## 1. What this codebase is

MedBridge AI is a **Streamlit multi-agent healthcare navigator** for Sri Lanka:

- Triage symptoms → specialty (never diagnose)
- Emergency regex → `tel:1990` + family push
- Book doctors (Pydantic AI + atomic SQL)
- Compare pharmacy prices (fuzzy + RAG)
- 3-specialist report panel + moderator
- Prescription OCR with human confirm gate
- EN / Sinhala / Tamil + voice

**Mental model — six layers**

```
CLIENT (browser, ntfy phone, tel:1990)
  → PRESENTATION  project/ui/          Streamlit panels
  → AGENTS        project/agents/      domain logic
  → INTELLIGENCE  project/llm.py + rag/
  → DATA          project/db/ + kb/ + Chroma
  → EXTERNAL      Gemini/OpenAI, ntfy, gTTS
```

**Golden rule:** panels never import each other’s agents. Chat writes `route_request`; domain panels consume it.

---

## 2. Full project tree (paths to remember)

```
MedBridge-AI/
├── Readme.md                      # Main project README
├── MedBridge_Viva_Guide.md        # Long viva study guide
├── VIVA_WRAP_UP_PLAN.md           # Solo viva execution plan
├── TRIAGE.md                      # Demo wart / checklist notes
├── pyproject.toml                 # ruff, black, pytest config
├── requirements.txt               # Root pointer / light deps
├── requirements-dev.txt           # pytest, ruff, black
├── .gitignore                     # ignores .env, venv, app.db, chroma
├── .streamlit/config.toml         # Theme / toolbar
│
├── docs/                          # Architecture + defense + demo docs
│   ├── architecture.md            # Mermaid six-layer + chat-turn
│   ├── architecture.html          # Browser-viewable diagrams
│   ├── architecture-1.png         # System diagram export
│   ├── architecture-2.png         # Chat-turn diagram export
│   ├── DEFENSE.md                 # Short viva Q&A answers
│   ├── TEAM_BRIEF.md              # Teammate prep note
│   ├── rag.md                     # RAG subsystem notes
│   ├── VIVA_PRESENTATION.md       # Slides + playthrough pack
│   ├── DEMO_WALKTHROUGH.md        # Setup + API key + demo
│   ├── DEMO_SCRIPT.md             # Spoken narration script
│   └── DEMO_STEPS_UPDATED.md      # OpenAI-live step checklist
│
├── tests/                         # 52 offline tests (no API key)
│   ├── conftest.py                # fixtures: seeded_db, no_api_key
│   ├── test_auth.py
│   ├── test_booking.py
│   ├── test_chatbot.py
│   ├── test_emergency.py
│   ├── test_i18n.py
│   ├── test_jsonutil.py
│   ├── test_medicine.py
│   ├── test_notifications.py
│   ├── test_rag.py
│   └── test_reminders.py
│
└── project/                       # ★ Application package
    ├── README.md                  # Tier 1/2/3 scope
    ├── requirements.txt           # Runtime deps (source of truth)
    ├── .env.example               # Template (safe to commit)
    ├── .env                       # ★ SECRETS — local only, gitignored
    ├── llm.py                     # Provider switch Gemini ↔ OpenAI
    ├── models.py                  # ALL Pydantic contracts (one file)
    ├── __init__.py
    │
    ├── agents/                    # Agent / domain logic layer
    ├── db/                        # SQLite schema, seed, connection
    ├── rag/                       # Chroma ingest + retrieve
    ├── i18n/                      # Translate + STT + TTS
    ├── notifications/             # ntfy.sh client
    ├── kb/                        # Seed JSON + demo samples
    └── ui/                        # Streamlit presentation
        ├── app.py                 # Entry: patient app :8501
        ├── supplier_portal.py     # Entry: supplier :8502
        ├── auth.py
        ├── common.py
        └── panels/                # One file per domain UI
```

---

## 3. Subtree deep dive

### 3.1 Root docs & tooling

| Path | Remember for |
|---|---|
| `Readme.md` | Features, setup, demo users |
| `docs/architecture.md` | “Walk me through architecture” |
| `docs/DEFENSE.md` | API / Streamlit / PDPA answers |
| `docs/VIVA_PRESENTATION.md` | Slides + code walk stops |
| `docs/DEMO_STEPS_UPDATED.md` | Live demo checklist |
| `MedBridge_Viva_Guide.md` | Deep study (800+ lines) |
| `pyproject.toml` | Tooling versions |
| `tests/` | Prove offline quality (52 tests) |

---

### 3.2 `project/` — core package

| Path | Role |
|---|---|
| `project/llm.py` | `generate_json`, `generate_text`, `ocr_image`, `transcribe_audio`, `pydantic_ai_model`, `crewai_model`. Reads `LLM_PROVIDER`. Never raises — returns empty on failure. |
| `project/models.py` | Single file of Pydantic models: `RouterOutput`, `BookingResponse`, `AlternativeSlot`, `ConsensusReport`, medicine quotes, etc. |
| `project/requirements.txt` | streamlit, crewai, pydantic-ai, google-generativeai, openai, chromadb deps, etc. |
| `project/.env` | Live keys — **never commit** |
| `project/.env.example` | Safe template with Gemini + OpenAI comments |

---

### 3.3 `project/agents/` — brain of the product

| Path | What it does | Key exports |
|---|---|---|
| `basic_chatbot.py` | Central message pipeline: persist → emergency → reminder → heuristic/LLM route → RAG ground → translate | `handle()`, `ground_specialty()`, `create_conversation()`, `load_history()` |
| `emergency.py` | Pure regex screener (~32 patterns, EN + romanised SI/TA). **No LLM.** | `screen()` |
| `booking_agent.py` | SQL find doctors/slots + `enrich_extracted` + Pydantic AI agent + atomic `book()` | `process()`, `process_agentic()`, `book()`, `enrich_extracted()` |
| `medicine_tracker.py` | Fuzzy + RAG match, pharmacy quotes, haversine sort | `process()`, `match_medicines()` |
| `specialist_panel.py` | 3 parallel CrewAI specialists (`ThreadPoolExecutor`) | `run_panel()` |
| `moderator.py` | Consensus + disagreement invariant (never empty list) | `synthesize()` |
| `vision_ocr.py` | Prescription image → text via `llm.ocr_image` | OCR helpers |
| `reminders.py` | Persist + fire future-visit reminders + ntfy | `fire()`, detection used from chatbot |
| `jsonutil.py` | Balanced-brace JSON extract from messy LLM text | `extract_json()` |

**Chat turn (remember this path through code):**

```
ui/panels/chat.py
  → agents/basic_chatbot.handle()
      → emergency.screen()          # first, no LLM
      → reminders (if not booking)
      → _heuristic_route() OR llm.generate_json()
      → ground_specialty() via rag/retriever
  → if domain: session_state["route_request"]
  → booking/medicine/report panel → its agent
```

---

### 3.4 `project/ui/` — presentation

| Path | Role |
|---|---|
| `ui/app.py` | **Patient entry.** `load_dotenv`, secrets bridge, `init_db`, RAG ensure, auth gate, call panels in order. Run: `streamlit run project/ui/app.py` → **:8501** |
| `ui/supplier_portal.py` | **Supplier concept demo.** Same DB. Pharmacy prices + hospital slots. Run → **:8502** |
| `ui/auth.py` | Signup/login, bcrypt, `current_user()`, session / `?uid=` remember-me |
| `ui/common.py` | Branding CSS, disclaimer, language helper, geolocation helpers |
| `ui/panels/__init__.py` | **Panel contract docs** — read this for architecture defense |

#### `project/ui/panels/` — one domain each

| Path | Consumes | Writes / shows |
|---|---|---|
| `sidebar.py` | user | Threads, language, city, family, ntfy hint, TTS, reminders, logout |
| `chat.py` | user text / voice | Only panel that calls `basic_chatbot.handle`; sets `route_request` or `pending_emergency` |
| `emergency.py` | `pending_emergency` | Confirm gate, tel:1990, ntfy |
| `booking.py` | `route_request` route=booking | Runs `process_agentic`, shows **table + Book**, `booking_success` |
| `medicine.py` | route=medicine | Pharmacy comparison dataframe |
| `report.py` | route=report_review | Specialist panel UI + moderator |
| `prescription.py` | uploads | OCR → confirm gate → medicine pending |
| `history.py` | DB | Read-only cross-domain timeline |

**Panel order in `app.py` (active panels above chat):**  
emergency → booking → medicine → report → prescription → history → chat

---

### 3.5 `project/db/` — data layer

| Path | Role |
|---|---|
| `schema.sql` | 17 tables (see §4) |
| `db.py` | Thread-local SQLite, `init_db()`, migrations, `get_conn()` |
| `seed.py` | Idempotent load from `kb/seed_*.json` (bcrypt passwords) |
| `app.db` | Runtime DB — **gitignored** |

**Init command:** `python -m project.db.db`

---

### 3.6 `project/rag/` — retrieval

| Path | Role |
|---|---|
| `embeddings.py` | Local ONNX default (`RAG_EMBED_BACKEND=local`) or Gemini |
| `ingest.py` | Build Chroma collections from kb + DB; `ensure_ingested()` |
| `retriever.py` | `retrieve(query, collection, k)` — returns `[]` never raises |

**Collections (typical):** symptoms / facilities / medicines  
**Command:** `python -m project.rag.ingest`

---

### 3.7 `project/i18n/` — language & voice

| Path | Role |
|---|---|
| `translate.py` | Static EN/SI/TA catalog `t(key, lang)` + `translate_dynamic()` via LLM |
| `stt.py` | Speech-to-text (Gemini or OpenAI Whisper via `llm`) |
| `tts.py` | gTTS voice out (no API key) |

---

### 3.8 `project/notifications/`

| Path | Role |
|---|---|
| `ntfy_client.py` | `send()`, `topic_for_user()` → `https://ntfy.sh/{prefix}-{user_id}`; audits `NotificationLog` |

Types: emergency, booking_confirmed, report_review_complete, prescription_confirmed, reminders.

---

### 3.9 `project/kb/` — seed & demo assets

| Path | Role |
|---|---|
| `seed_users.json` | demo1–demo6 (+ passwords hashed on load) |
| `seed_facilities.json` | Hospitals, doctors, **day_offset slots** (Dr. Sunil Perera demo) |
| `seed_medicines.json` | Catalog + reference dosage text |
| `seed_pharmacy_prices.json` | Per-pharmacy prices / stock (Losartan demo) |
| `rag_knowledge/symptom_specialty.json` | Curated symptom → specialty notes |
| `sample_reports/*.txt` | Demo reports (use **ambiguous** for disagreement) |
| `sample_prescriptions/sample_rx_en.png` | Demo Rx image |
| `sample_prescriptions/sample_rx_en.txt` | Paste-path fallback text |

---

### 3.10 `tests/` — offline proof

| Path | Covers |
|---|---|
| `conftest.py` | Temp DB seed, wipe API key fixtures |
| `test_emergency.py` | Regex matches |
| `test_booking.py` | Slots, book atomicity, enrich paths |
| `test_chatbot.py` | Routing / handle |
| `test_medicine.py` | Matching / quotes |
| `test_rag.py` | Offline retrieve safety |
| others | auth, i18n, jsonutil, notifications, reminders |

**Run:** `pytest -q` (no key needed)

---

## 4. Database tables (17) — split for viva

**User / system-of-record (production-correct):**  
`User` · `Conversation` · `ChatMessage` · `Appointment` · `Prescription` · `MedicalReport` · `SpecialistOpinion` · `ConsensusReport` · `FutureVisitReminder` · `NotificationLog`

**Marketplace catalog (seed today → supplier portal tomorrow):**  
`Specialty` · `Facility` · `Doctor` · `AppointmentSlot` · `Medicine` · `Pharmacy` · `PharmacyMedicinePrice`

Schema file: `project/db/schema.sql`

---

## 5. Paths ranked — memorize these first

### Must-open in viva

1. `project/ui/app.py` — thin shell entry  
2. `project/agents/basic_chatbot.py` — `handle()` pipeline  
3. `project/agents/emergency.py` — regex before LLM  
4. `project/agents/booking_agent.py` — enrich + tools + `book()`  
5. `project/ui/panels/booking.py` — table + Book UI  
6. `project/llm.py` — provider switch  
7. `project/ui/supplier_portal.py` — two-sided platform proof  
8. `docs/architecture.md` — diagram source  
9. `docs/DEFENSE.md` — short answers  
10. `project/db/schema.sql` — 17 tables  

### Demo asset paths

| Demo moment | Path |
|---|---|
| Ambiguous report | `project/kb/sample_reports/report_ambiguous_findings.txt` |
| Rx image | `project/kb/sample_prescriptions/sample_rx_en.png` |
| Seed doctor slots | `project/kb/seed_facilities.json` → Dr. Sunil Perera |
| Losartan stock | `project/kb/seed_pharmacy_prices.json` |

### Config paths

| Purpose | Path |
|---|---|
| Secrets | `project/.env` (local) |
| Template | `project/.env.example` |
| Theme | `.streamlit/config.toml` |
| Runtime DB | `project/db/app.db` |

---

## 6. Session-state signals (UI glue)

| Key | Set by | Consumed by |
|---|---|---|
| `route_request` | `chat.py` | booking / medicine / report panels |
| `pending_emergency` | `chat.py` | `emergency.py` |
| `pending_booking` | `booking.py` | itself (table render) |
| `booking_success` | `booking.py` | success card after rerun |
| `pending_medicine` | medicine / prescription | `medicine.py` |
| `pending_rx` | `prescription.py` | confirm gate |
| `active_conversation_id` | chat / sidebar | history load |
| `tts_on` | sidebar | chat TTS |

---

## 7. How to run (quick)

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1

# Patient
streamlit run project\ui\app.py          # :8501

# Supplier
streamlit run project\ui\supplier_portal.py --server.port 8502

# DB reset + seed
python -m project.db.db

# Tests
pytest -q
```

Demo logins: `demo1`/`demo1pass` · `demo3`/`demo3pass` (SI) · `demo4`/`demo4pass` (TA)

---

## 8. Ownership map (who coded what)

| Person | Paths |
|---|---|
| **Janidu** | `basic_chatbot.py`, `emergency.py`, `rag/`, `app.py`, `chat.py`, `sidebar.py`, `history.py` |
| **Thevindu** | `booking_agent.py`, `reminders.py`, `panels/booking.py` |
| **Nisal** | `medicine_tracker.py`, `vision_ocr.py`, `i18n/`, `panels/medicine.py`, `panels/prescription.py` |
| **Chanupa** | `auth.py`, `db/`, `specialist_panel.py`, `moderator.py`, `notifications/`, `panels/report.py` |

---

## 9. Design lines worth quoting

1. **Thin shell, fat panels** — `app.py` only orchestrates.  
2. **`route_request` decoupling** — four people, no merge hell.  
3. **Heuristic-first routing** — booking/medicine/report skip LLM hang.  
4. **Structural safety** — regex emergency, confirm gates, atomic book, moderator invariant.  
5. **Graceful degradation** — every LLM path has deterministic fallback.  
6. **Typed tools** — agents don’t invent doctors/slots; SQL is source of truth.  
7. **Two-sided platform** — supplier portal writes same tables seed writes.

---

## 10. What is NOT in git (local only)

| Path | Why |
|---|---|
| `project/.env` | API keys |
| `project/venv/` | Virtualenv |
| `project/db/app.db` | Local SQLite |
| Chroma persist dir | Vector index cache |
| This file (if you keep it untracked) | Local study sheet |

---

**One-sentence codebase summary:**  
Streamlit panels signal domain intents into Python agents that talk to SQLite + offline RAG through a provider-agnostic LLM layer, with safety enforced in code before and around every model call.
