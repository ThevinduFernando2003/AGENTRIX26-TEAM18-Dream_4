# MedBridge AI — Full Viva Presentation Pack

**Team:** Dream_4 (TEAM18) · AgenTrix 2026  
**Branch:** `viva-prep` (polish repo — architecture identical to frozen hackathon repo)  
**Demo length:** 10–12 minutes live + slides (~8–10 min) + Q&A  
**Apps:** Patient `localhost:8501` · Supplier portal `localhost:8502`

> **One-line thesis:** MedBridge is a healthcare *navigator*, never a diagnoser — multi-agent orchestration with **structural safety** and **graceful degradation**, free-tier only.

Use this file as: (1) slide script, (2) live demo playbook, (3) codebase walkthrough cue cards. Companion files: [`DEFENSE.md`](DEFENSE.md) · [`architecture.html`](architecture.html) · [`../MedBridge_Viva_Guide.md`](../MedBridge_Viva_Guide.md).

---

# PART A — Slide Deck (18 slides)

Copy each slide into PowerPoint / Google Slides. Keep visuals sparse: title + 3–5 bullets max. Open `docs/architecture.html` (or the PNGs) on slides 5–6 instead of redrawing.

---

## SLIDE 1 — Title

**MedBridge AI**  
Multi-agent healthcare navigator for Sri Lanka

- AgenTrix 2026 · Team Dream_4 (TEAM18)
- Chanupa · Thevindu · Nisal · Janidu
- Tagline on screen: *Navigate care. Never diagnose.*

**Say:** “We built a trilingual multi-agent system that helps patients find the right care path — specialists, bookings, medicines, report review — without ever acting as a doctor.”

---

## SLIDE 2 — Problem

**Fragmented healthcare access in Sri Lanka**

| Pain | Reality |
|---|---|
| Which specialist? | Patients guess or wait |
| Booking | No open channeling API |
| Medicine prices / stock | No public pharmacy API |
| Language | Sinhala / Tamil / English |
| Emergencies | Delay before calling 1990 |

**Say:** “The domain problem *is* fragmentation. Closed systems (eChannelling, Doc990) and no open pharmacy APIs — so a navigator that owns its marketplace data layer is the right product shape.”

---

## SLIDE 3 — Solution (what we built)

**One chat. Five agent groups. Structural safety.**

1. **Triage chatbot** — symptom → specialty (never disease)
2. **Emergency screener** — regex *before* any LLM → `tel:1990` + family push
3. **Booking agent** — Pydantic AI + atomic SQL
4. **Medicine tracker** — fuzzy + RAG, cost then distance
5. **Specialist panel + moderator** — 3 independent CrewAI agents
6. **Bonus:** prescription OCR (confirm gate) · reminders · voice · EN/SI/TA

**Say:** “Safety is enforced in code, not prompts. Every AI feature has a deterministic fallback — the full demo runs with no API key.”

---

## SLIDE 4 — Demo agenda (what you will see live)

| # | Moment | Proof |
|---|---|---|
| 1 | Chest pain → 1990 + ntfy | Regex before LLM |
| 2 | Book Dr. Sunil · conflict → alternatives | Typed tools + atomic book |
| 3 | Panadol + Amoxicillin prices | RAG + complete-basket sort |
| 4 | **Supplier portal** toggle Losartan | Two-sided platform |
| 5 | Ambiguous report → 3 specialists | Parallel CrewAI + disagreement guard |
| 6 | Rx OCR → confirm → pharmacies | Human-in-the-loop |
| 7 | Sinhala + reminder | i18n + voice |

---

## SLIDE 5 — Architecture (six layers)

**Show:** `docs/architecture-1.png` or open `architecture.html`

```
CLIENT → PRESENTATION (Streamlit panels)
      → AGENTS (chat · emergency · booking · medicine · panel · OCR · reminders)
      → INTELLIGENCE (llm.py provider switch · RAG)
      → DATA (SQLite 17 tables · ChromaDB · seed JSON)
      → EXTERNAL (Gemini/OpenAI · ntfy · gTTS)
```

**Say:** “Presentation is a thin shell. Agents talk to panels only via `route_request` in session state. Swap Streamlit for FastAPI + React later — one layer changes.”

---

## SLIDE 6 — One chat turn (request lifecycle)

**Show:** `docs/architecture-2.png`

```
User message
  → persist ChatMessage
  → emergency.screen()          ← NO LLM
  → reminder detect (if not booking)
  → heuristic route (booking/medicine/report) OR llm.generate_json()
  → ground_specialty() via RAG
  → translate if si/ta
  → set route_request → domain panel → agent → SQLite / ntfy
```

**Say:** “Heuristic-first routing: unambiguous intents skip the LLM. Ambiguous ‘general’ messages get one timed JSON call (8s, no retries).”

---

## SLIDE 7 — GitHub / repo tree

```
MedBridge-AI / AGENTRIX26-TEAM18-Dream_4
├── Readme.md · pyproject.toml · requirements*.txt
├── docs/          architecture · DEFENSE · this presentation
├── tests/         52 offline pytest (no API key)
└── project/
    ├── llm.py          ★ provider-agnostic LLM (viva-prep)
    ├── models.py       all Pydantic contracts
    ├── agents/         chatbot · booking · emergency · medicine ·
    │                   specialist_panel · moderator · OCR · reminders
    ├── db/             schema.sql · db.py · seed.py
    ├── rag/            embeddings · ingest · retriever
    ├── i18n/           translate · tts · stt
    ├── notifications/  ntfy_client
    ├── kb/             seed JSON · sample reports · Rx
    └── ui/
        ├── app.py              patient entry (8501)
        ├── supplier_portal.py  ★ concept demo (8502)
        └── panels/             sidebar · chat · emergency · booking ·
                                medicine · report · prescription · history
```

**Say:** “Panel contract: every panel is `render(user)`. Four developers owned verticals without merge hell.”

---

## SLIDE 8 — Tech stack & why

| Choice | Why |
|---|---|
| **Streamlit** | 12-hour hackathon · pure Python · parallel panels |
| **CrewAI** | Specialist panel roles + parallel independence |
| **Pydantic AI** | Typed booking tools — model cannot invent slots |
| **Gemini 2.5 Flash** | Free multimodal (text/image/audio) |
| **`llm.py` switch** | Rehearse on OpenAI without burning Gemini quota |
| **Chroma + ONNX** | Offline RAG, no quota, never raises |
| **SQLite** | Zero-config ACID booking (`slot_id UNIQUE`) |
| **ntfy.sh** | Free family push + audit log |

---

## SLIDE 9 — Structural safety (memorize)

| Guarantee | Enforcement |
|---|---|
| Never diagnose | UI disclaimer · symptom→specialty only |
| Emergency first | 32 regex patterns before any network |
| No hallucinated bookings | LLM proposes · `book()` writes atomically |
| OCR safety | Confirm gate before pharmacy lookup |
| Dosage safety | Catalog `reference_dosage_text` only |
| Disagreement visible | Moderator invariant — list never empty |
| Offline-safe | Every agent has deterministic fallback |

**Closing line:** “We don’t trust the LLM to be safe — we make safety structural.”

---

## SLIDE 10 — Code map (who owns what)

| Member | Vertical | Key files |
|---|---|---|
| **Janidu** | RAG, chatbot, emergency, shell | `basic_chatbot.py` · `emergency.py` · `rag/` · `app.py` · chat/sidebar |
| **Thevindu** | Booking + reminders | `booking_agent.py` · `reminders.py` · `panels/booking.py` |
| **Nisal** | Medicine + Rx + i18n | `medicine_tracker.py` · `vision_ocr.py` · `i18n/` |
| **Chanupa** | Auth, DB, panel, ntfy | `auth.py` · `db/` · `specialist_panel.py` · `moderator.py` |

---

## SLIDE 11 — Database (17 tables, split the story)

**System-of-record (production-correct):**  
`User` · `Conversation` · `ChatMessage` · `Appointment` · `Prescription` · `MedicalReport` · `FutureVisitReminder` · `NotificationLog`

**Marketplace catalog (seed today → supplier portal tomorrow):**  
`Facility` · `Doctor` · `AppointmentSlot` · `Medicine` · `Pharmacy` · `PharmacyMedicinePrice` · …

**Say:** “User tables are real. Catalog tables are labeled SEED — and the supplier portal writes the *same* rows a pharmacy would in production.”

---

## SLIDE 12 — viva-prep addons (what’s new vs frozen repo)

| Addon | Why it matters |
|---|---|
| **`project/llm.py`** | `LLM_PROVIDER=gemini\|openai` — no code change to swap |
| **Supplier portal :8502** | Live proof of two-sided platform |
| **Architecture diagrams** | Answer “walk me through architecture” |
| **Defense pack** | DEFENSE.md · Viva Guide · wrap-up plan |
| **Booking success card** | Survives `st.rerun()` |
| **Medicine sort + LKR polish** | Complete baskets rank first |
| **Rx Step 1→2→3 markers** | Confirm gate is visible |
| **Sidebar ntfy hint** | Copyable family subscribe URL |
| **i18n keys** | New UI strings in EN/SI/TA |

**If asked why demo ≠ frozen repo:**  
“Frozen repo is our untouched 12-hour state (rule 4). Architecture identical; this branch is polish + docs + LLM abstraction + supplier-portal concept.”

---

## SLIDE 13 — Setup (how we run it)

```bash
python -m venv project/venv
project\venv\Scripts\activate          # Windows
pip install -r project/requirements.txt
cp project/.env.example project/.env   # GEMINI_API_KEY or OPENAI_*
python -m project.db.db                # schema + seed
streamlit run project/ui/app.py        # :8501
streamlit run project/ui/supplier_portal.py --server.port 8502
pytest                                 # 52 offline tests
```

**Demo users:** `demo1` / `demo1pass` · `demo3` (Sinhala) · `demo4` (Tamil)

---

## SLIDE 14 — Live demo (transition slide)

**Now: live walkthrough**

Keep this slide up while driving the app. Narrators follow Part B below.

---

## SLIDE 15 — Two-sided platform (after portal moment)

**Suppliers publish INTO MedBridge — we fetch nothing.**

```
Pharmacy dashboard ──UPDATE──► PharmacyMedicinePrice
Hospital admin     ──INSERT──► AppointmentSlot
                         │
                         ▼
              Patient agents (typed tools)
```

Same model as eChannelling / PickMe. Seed loader ≈ supplier portal stand-in. Portal demo makes it literal.

---

## SLIDE 16 — Production path (scope armor)

| Prototype | Production |
|---|---|
| Streamlit | FastAPI + React / mobile |
| SQLite | Postgres + encryption |
| `?uid=` remember-me | Signed sessions / JWT |
| ntfy topics | Authenticated push (FCM) |
| Seed + portal concept | Supplier accounts + POS adapters |

**Say:** “Validated prototype on purpose — multi-agent orchestration, structural safety, marketplace data layer. Everything else is roadmap, not gap.”

---

## SLIDE 17 — Results & evidence

- **52 offline tests** green (no API key)
- **Trilingual** EN / Sinhala / Tamil + voice I/O
- **Free-tier only** — Gemini / OpenAI / ntfy / gTTS / local ONNX
- **Graceful degradation** — kill the key, demo still runs
- **Parallel team** via panel contract

---

## SLIDE 18 — Close + Q&A

**MedBridge AI — navigate care, never diagnose.**

> “Turn the API key off and this entire demo still runs on deterministic fallbacks. Structural safety. Graceful degradation.”

Questions?

---

# PART B — Live Demo Playthrough (10–12 min)

**Driver:** Janidu (or designated) · **Others narrate their verticals**  
**Pre-open tabs:** Patient app · Supplier portal · ntfy on phone · architecture diagram · DEFENSE.md · backup recording

### Pre-flight (45 min before)

1. Delete `project/db/app.db` + chroma store → clean boot
2. `.env` has key (`GEMINI_API_KEY` or `LLM_PROVIDER=openai` + `OPENAI_API_KEY`)
3. `streamlit run project/ui/app.py` → login `demo1` / `demo1pass`
4. Sidebar: city = Colombo · subscribe phone to `https://ntfy.sh/medbridge-demo-{user_id}`
5. Start supplier portal on **8502**
6. One silent dry-run of steps 1–7

---

### Minute-by-minute script

| Time | Action | Exact prompt / click | Narrator | Line to say |
|---|---|---|---|---|
| **0:00–0:30** | Intro | Stay on Slide 3 or app home | Janidu | “Healthcare *navigator*, never a diagnoser — five agent groups, free-tier, every AI feature has a deterministic fallback.” |
| **0:30–1:45** | Emergency | `I have severe chest pain and can't breathe` → **Confirm** → show `tel:1990` + phone buzz | Janidu | “Pure regex, ~32 patterns, runs *before* any LLM — zero latency on the safety path. Family gets ntfy.” |
| **1:45–3:30** | Booking | `Book me with Dr. Sunil Perera tomorrow at 10:00` → pick alternative → **Book** → green success card | Thevindu | “Pydantic AI proposes via typed SQL tools; only `book()` writes — atomic transaction, slot UNIQUE. Success card persists after rerun.” |
| **3:30–4:45** | Medicine | `I need prices for Panadol and Amoxicillin` | Nisal | “Fuzzy + RAG match with precision guard. Complete baskets rank above partial; LKR + distance.” |
| **4:45–6:15** | **Supplier portal** | Port 8502 → Union Chemists → toggle **Losartan** in-stock → Publish → back to patient → `price of Losartan` | Janidu | “Two-sided platform: suppliers publish, patients see it — platform is source of truth, no third-party API dependency.” |
| **6:15–8:00** | Specialist panel | Report flow → `report_ambiguous_findings.txt` → run panel → show 3 columns + moderator disagreement | Chanupa | “Three specialists, separate threads, no shared state. Disagreement list can never be empty — code invariant.” |
| **8:00–9:15** | Prescription | Upload `sample_rx_en.png` → edit/confirm (Step 1→2→3) → pharmacy table | Nisal | “Nothing runs until the human confirms. Dosage only from catalog text.” |
| **9:15–10:30** | i18n + reminder | Logout → `demo3` / `demo3pass` → one Sinhala turn → `come back in 2 weeks` → Reminders → push | Janidu | “Trilingual catalog + dynamic translation. Reminders are regex, idempotent, yield to booking intent.” |
| **10:30–11:00** | Close | Optional: mention “key off still works” | Janidu | “Structural safety. Graceful degradation. Happy to take questions.” |

### Contingencies

| Failure | Response |
|---|---|
| Gemini 429 / slow | Fallbacks engage — “designed behavior, not a crash” |
| App crash | Switch to backup screen recording; narrate over it |
| ntfy silent | Open History / show `NotificationLog` — “every attempt audited” |
| Portal broken | Skip step 5; deliver two-sided platform verbally (DEFENSE §3) |

---

# PART C — Codebase Walkthrough (for “prove you wrote this”)

Use when evaluators ask to open the IDE. Walk **top-down**, 60–90 seconds per stop.

### Stop 1 — Entry shell
**File:** `project/ui/app.py`  
- Page config · secrets→env bridge · `init_db()` · `ensure_ingested()` · auth gate · call each panel `render()`  
- **Point:** thin shell; no domain logic here.

### Stop 2 — Chat router
**File:** `project/agents/basic_chatbot.py` → `handle()`  
1. Persist user message  
2. `emergency.screen()` first  
3. Reminder detect (if not booking)  
4. Heuristic route OR `llm.generate_json()` (8s timeout)  
5. `ground_specialty()` via RAG  
6. Translate · persist assistant message  

### Stop 3 — Emergency (no LLM)
**File:** `project/agents/emergency.py`  
- Pattern list · romanised SI/TA · returns match → panel shows confirm + `tel:1990`

### Stop 4 — Booking (typed agent)
**File:** `project/agents/booking_agent.py`  
- `process_agentic()` — Pydantic AI + SQL tools  
- `book()` — only path that INSERTs `Appointment` (transaction)  
- LLM `status='booked'` is **downgraded** until user clicks Book

### Stop 5 — Medicine
**File:** `project/agents/medicine_tracker.py`  
- Match: substring → difflib → RAG (precision guard)  
- `quotes_for()` · haversine · sort complete baskets → total → distance

### Stop 6 — Specialist panel + moderator
**Files:** `specialist_panel.py` · `moderator.py`  
- `ThreadPoolExecutor(3)` · fresh Crew each  
- `_ensure_invariants()` forces non-empty disagreement

### Stop 7 — LLM abstraction (viva-prep)
**File:** `project/llm.py`  
- `LLM_PROVIDER` → `generate_json` / `generate_text` / `ocr_image` / `transcribe_audio` / `pydantic_ai_model`  
- Agents import `llm`, never Gemini/OpenAI SDKs directly

### Stop 8 — Supplier portal (viva-prep)
**File:** `project/ui/supplier_portal.py`  
- Same `get_conn()` · UPDATE prices / INSERT slots · no schema change

### Stop 9 — Data + RAG
**Files:** `project/db/schema.sql` · `project/rag/retriever.py`  
- 17 tables · `retrieve()` returns `[]` never raises

### Stop 10 — Tests
**Folder:** `tests/` — 52 offline · `conftest.py` fixtures wipe API key

---

# PART D — Full Setup Card (print / pin)

### Environment

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Default path (`gemini-2.5-flash`) |
| `LLM_PROVIDER=openai` | Switch without code changes |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | gpt-4o-mini path |
| `RAG_EMBED_BACKEND=local` | ONNX embeddings (default) |
| `NTFY_TOPIC_PREFIX` | `medbridge-demo` |
| `SUPPLIER_PASSCODE` | Optional portal gate |

### Commands

```bash
# Patient
streamlit run project/ui/app.py

# Supplier
streamlit run project/ui/supplier_portal.py --server.port 8502

# DB reset
python -m project.db.db

# RAG (optional — also auto on first run)
python -m project.rag.ingest

# Tests
pip install -r requirements-dev.txt
pytest -q
```

### Seed logins

| User | Password | Lang |
|---|---|---|
| demo1 | demo1pass | EN |
| demo2 | demo2pass | EN |
| demo3 | demo3pass | SI |
| demo4 | demo4pass | TA |
| demo5 / demo6 | demo5pass / demo6pass | EN |

---

# PART E — Q&A Cue Cards (30-second answers)

**1. Walk through architecture** → Six layers (Slide 5) then chat-turn (Slide 6). Point at diagram.

**2. LLM down?** → Heuristics, English stubs, paste-path OCR, regex emergency/reminders. App never crashes.

**3. Why Streamlit?** → 12h constraint · panel parallelization · thin presentation layer · production = FastAPI + React.

**4. Data is fake?** → Split schema (Slide 11) · no open SL APIs · typed tool seam · **show portal**.

**5. Medical privacy?** → bcrypt · user_id scoping · UI disclaimers · OCR gate · NotificationLog · PDPA special category posture · volunteer: unsigned `?uid=`, SQLite at rest, guessable ntfy (demo-grade).

**6. Prove authorship?** → `git log --author` + walk your files (Part C).

**7. 10k users?** → Postgres · stateless API · FCM · paid LLM / self-host · horizontal workers.

**8. NFRs?** → Security · PDPA · graceful degradation · heuristic-first latency · trilingual UX · 52 tests · free-tier cost.

**9. Two more weeks?** → Supplier accounts · signed sessions · Postgres · retrieval eval · one pharmacy pilot.

**10. Demo ≠ frozen repo?** → Rule 4 polish repo; architecture identical; addons = portal + llm.py + docs + UI polish.

---

# PART F — Presenter Checklist (day-of)

- [ ] On `viva-prep`, pulled latest
- [ ] Patient app running (8501), portal (8502)
- [ ] Phone subscribed to ntfy topic
- [ ] Slides 1–18 ready; architecture tab open
- [ ] Backup recording ready
- [ ] Each member knows their narration slot (Part B table)
- [ ] DEFENSE.md skimmed once aloud
- [ ] Drift list owned (models.py not package · Conversation not ChatSession · direct JSON router not CrewAI for chat · gemini-2.5-flash)

---

**End of presentation pack.** Rehearse Part B once timed ≤ 12 minutes. Memorize Slides 3, 9, 12, 15 and DEFENSE sections 1–4.
