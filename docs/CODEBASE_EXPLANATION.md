# MedBridge AI — Codebase Explanation & Path Map

**Study sheet for viva / defense + Phase 0/1 orientation.**  
**Branch:** `booking` (publish to `origin` only).  
**Status:** [`PHASE_STATUS.md`](PHASE_STATUS.md) · **Tests:** ≈85 offline (`pytest --collect-only`)

---

## 1. What this codebase is

MedBridge AI is a **Streamlit multi-agent healthcare navigator** for Sri Lanka:

- Triage symptoms → specialty (never diagnose)
- Emergency regex → `tel:1990` + family ntfy (+ optional SMS)
- Book / cancel / reschedule doctors (Pydantic AI + atomic SQL)
- Compare pharmacy prices (fuzzy + RAG) with freshness badges
- 3-specialist report panel + moderator
- Prescription OCR with human confirm gate
- EN / Sinhala / Tamil + voice
- Two-sided supplier portal (RBAC: pharmacy / hospital staff)

**Mental model — six layers**

```
CLIENT (browser, ntfy phone, tel:1990, SMS)
  → PRESENTATION  project/ui/          Streamlit panels
  → AGENTS/SERVICES  agents + hospital/pharmacy_service + authz
  → INTELLIGENCE  project/llm.py + rag/
  → DATA          project/db/ (repo seam) + kb/ + Chroma
  → EXTERNAL      Gemini/OpenAI, ntfy, SMS stub/http, gTTS
```

**Golden rule:** panels never import each other’s agents. Chat writes `route_request`; domain panels consume it.

---

## 2. Full project tree (paths to remember)

```
MedBridge-AI/
├── Readme.md
├── pyproject.toml
├── requirements.txt               # Streamlit Cloud pin set
├── requirements-dev.txt           # CI / local pytest
├── .github/workflows/ci.yml
│
├── docs/
│   ├── PHASE_STATUS.md            # ★ What is done (P0 + P1.1–1.7)
│   ├── DEPLOY_RENDER.md           # Host Streamlit (not Vercel)
│   ├── SRS.md / SAD.md / IMPLEMENTATION_PLAN.md
│   ├── UAT_CHECKLIST.md / SAFETY_CHECKLIST.md
│   ├── CODEBASE_EXPLANATION.md    # this file
│   ├── DEMO_*.md / DEFENSE.md / architecture.md
│   └── …
│
├── tests/                         # ≈85 offline tests
│   ├── conftest.py
│   ├── test_auth.py / test_authz.py / test_booking.py
│   ├── test_hospital_service.py / test_pharmacy_service.py
│   ├── test_sms_notify.py / test_pg_compat.py / test_repo.py
│   └── …
│
└── project/
    ├── llm.py                     # Gemini ↔ OpenAI; GoogleModel for pydantic-ai
    ├── authz.py                   # RBAC helpers
    ├── supplier_auth.py           # Staff login → User roles
    ├── hospital_service.py        # Today / no-show / templates
    ├── pharmacy_service.py        # CSV import
    ├── models.py
    ├── agents/                    # booking, medicine, emergency, …
    ├── workers/reminder_worker.py
    ├── db/
    │   ├── schema.sql / db.py / seed.py
    │   ├── repo.py                # repository seam
    │   └── pg_compat.py           # optional Postgres shim
    ├── notifications/
    │   ├── ntfy_client.py
    │   ├── sms_client.py
    │   └── notify.py              # emergency orchestration
    ├── kb/                        # seed_*.json including seed_suppliers.json
    ├── rag/
    ├── i18n/
    └── ui/
        ├── app.py                 # patient :8501
        ├── supplier_portal.py     # supplier :8502
        ├── auth.py
        └── panels/                # + appointments.py
```

---

## 3. Critical flows (viva)

| Flow | Entry | Core |
|---|---|---|
| Chat route | `panels/chat.py` | `basic_chatbot.handle` → `route_request` |
| Booking | `panels/booking.py` | `booking_agent.process*` → `book()` only writer |
| Cancel / reschedule | `panels/appointments.py` | `cancel` / `reschedule` |
| Medicine | `panels/medicine.py` | `match_medicines` → `quotes_for` + freshness |
| Emergency | `panels/emergency.py` | regex first → `notify_emergency_family` |
| Staff | `supplier_portal.py` | `supplier_auth.login` + authz scope |
| Reminders | sidebar + worker | `reminders.process_due` |

---

## 4. Safety invariants (never break)

1. Emergency **before** LLM  
2. OCR **confirm** before pharmacy lookup  
3. Only `book()` / cancel / reschedule write appointments (LLM cannot force booked)  
4. Moderator disagreement non-empty  
5. Dosage from catalog text only  

See [`SAFETY_CHECKLIST.md`](SAFETY_CHECKLIST.md).

---

## 5. Run locally

```bash
pip install -r requirements-dev.txt
cp project/.env.example project/.env   # set GEMINI_API_KEY or OPENAI_*
python -m project.db.db
python -m project.rag.ingest           # optional
streamlit run project/ui/app.py
# other terminal:
streamlit run project/ui/supplier_portal.py --server.port 8502
# optional:
python -m project.workers.reminder_worker --once
pytest -q
```

**Staff SEED:** `union` / `unionpass` · `nawaloka` / `nawalokapass`  
**Patient SEED:** `demo1` / `demo1pass`

---

## 6. Hosting (short)

| Target | OK? |
|---|---|
| Render / Streamlit Cloud (full Streamlit) | Yes — [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) |
| Vercel as the website today | No — not a Next/React app yet |
| Vercel + Render API | Phase 2 after FastAPI + PWA |

---

## 7. Related docs

| Need | Doc |
|---|---|
| What’s done | [`PHASE_STATUS.md`](PHASE_STATUS.md) |
| Requirements | [`SRS.md`](SRS.md) |
| Architecture | [`SAD.md`](SAD.md) · [`architecture.md`](architecture.md) |
| UAT | [`UAT_CHECKLIST.md`](UAT_CHECKLIST.md) |
| Demo | [`DEMO_STEPS_UPDATED.md`](DEMO_STEPS_UPDATED.md) |
