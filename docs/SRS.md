# MedBridge AI — Software Requirements Specification (SRS)

**Project:** MedBridge AI · AgenTrix 2026 · Team Dream_4 (TEAM18)  
**Version:** 1.1 (post-viva polish + upgrade roadmap)  
**Status:** Living document — derived from `Readme.md` tiers, `docs/architecture.md`, `docs/DEFENSE.md`, and implemented code  
**Related:** [`SAD.md`](SAD.md) · [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) · [`DEFENSE.md`](DEFENSE.md)

---

## 1. Introduction

### 1.1 Purpose

This SRS defines functional and non-functional requirements for MedBridge AI: a multi-agent healthcare **navigator** for Sri Lanka. It distinguishes **as-built prototype** requirements from **production target** requirements.

### 1.2 Scope

**In scope**

- Patient conversational navigation (triage → specialty, never diagnosis)
- Emergency screening, booking, medicine comparison, Rx OCR, specialist report panel
- Trilingual UI (EN/SI/TA) and voice I/O
- Two-sided marketplace model (hospitals/pharmacies publish into the platform)
- Structural safety and graceful LLM degradation

**Out of scope (non-goals)**

- Automated medical diagnosis or disease labeling as clinical truth
- Autonomous prescribing or dosage invention
- Claiming live hospital/pharmacy feeds without supplier accountability

### 1.3 Definitions

| Term | Meaning |
|---|---|
| Navigator | Suggests care path / logistics; does not diagnose |
| SEED data | Curated demo catalog labeled “not live” |
| Structural safety | Enforced in code (regex, confirm gates, atomic SQL), not prompts alone |
| `route_request` | Session signal from chat panel to domain panels |

### 1.4 References

- `Readme.md`, `project/README.md` — feature tiers  
- `docs/architecture.md` — system diagrams  
- `docs/DEFENSE.md` — production path & compliance posture  
- `docs/UPGRADE_PLAN.md` — phased roadmap  

---

## 2. Overall description

### 2.1 Product perspective

MedBridge is a **two-sided platform**:

- **Demand side:** patients (and caregivers)  
- **Supply side:** hospitals/clinics (slots) and pharmacies (prices/stock)  

Sri Lanka lacks open public channeling/pharmacy-stock APIs; suppliers publish **into** MedBridge. Agents consume data only through typed tools.

### 2.2 User classes

| User | Description |
|---|---|
| Patient | Primary end user of the chat app |
| Family contact | Receives emergency/booking/reminder alerts |
| Hospital staff | Publishes doctors/slots; manages bookings (target) |
| Pharmacy staff | Publishes prices/stock (target; concept portal today) |
| Platform admin | Ops, compliance, content (target) |

### 2.3 Operating environment (as-built)

- Python 3.11+ (3.13 used in polish env)  
- Streamlit patient app `:8501`, supplier portal `:8502`  
- SQLite + ChromaDB (local ONNX embeddings)  
- LLM: Gemini or OpenAI via `LLM_PROVIDER`  
- Notifications: ntfy.sh  

### 2.4 Constraints

- Free-tier / competition constraints shaped the prototype  
- No diagnosis language on clinical surfaces  
- SEED catalogs must remain labeled until live suppliers exist  
- PDPA (Sri Lanka) treats health data as special category  

---

## 3. Functional requirements

Legend: **✅** as-built · **⚠️** partial · **❌** missing (target)

| ID | Requirement | Status |
|---|---|---|
| FR-01 | User signup/login with bcrypt-hashed passwords | ✅ |
| FR-02 | Multi-conversation chat with persistent history | ✅ |
| FR-03 | Emergency regex screen **before** any LLM; confirm; `tel:1990` | ✅ |
| FR-04 | Family alerts on emergency/booking/report/Rx/reminders | ⚠️ ntfy topic (phone unused for SMS) |
| FR-05 | Symptom → specialty navigation via RAG; UI disclaimer | ✅ |
| FR-06 | Book doctor; alternatives if full; atomic `book()` write | ✅ |
| FR-07 | Medicine price/stock/distance comparison | ✅ |
| FR-08 | Prescription OCR with human confirm before pharmacy lookup | ✅ |
| FR-09 | Three independent specialist agents + moderator; disagreement non-empty | ✅ |
| FR-10 | EN / Sinhala / Tamil UI; STT/TTS paths | ✅ |
| FR-11 | Future-visit reminder detect + notify | ⚠️ manual fire only |
| FR-12 | Pharmacy publishes prices/stock into shared tables | ⚠️ concept portal |
| FR-13 | Hospital publishes appointment slots | ⚠️ concept portal |
| FR-14 | Pay channeling fee / receipts | ❌ |
| FR-15 | Admin console (users, audit, flags) | ❌ |
| FR-16 | Cross-domain patient activity history | ✅ read-only |
| FR-17 | Provider-agnostic LLM switch (`gemini` \| `openai`) | ✅ |
| FR-18 | Offline/deterministic fallbacks when API key absent | ✅ |
| FR-19 | Patient cancel/reschedule appointment | ❌ (cancel planned Phase 0) |
| FR-20 | Explicit consent capture for health-data processing | ❌ (Phase 0) |

---

## 4. Non-functional requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-01 | Safety: never diagnose; disclaimers on clinical UI | ✅ |
| NFR-02 | Reliability: LLM failure → graceful fallback | ✅ |
| NFR-03 | Performance: unambiguous domain routes without LLM hang | ✅ heuristic-first |
| NFR-04 | Privacy: PDPA-aligned handling of health data | ⚠️ partial |
| NFR-05 | Security: hashed passwords; user-scoped queries | ⚠️ demo auth (`?uid=` unsigned) |
| NFR-06 | Cost control: local embeddings default; timed LLM calls | ✅ |
| NFR-07 | Maintainability: panel contract + offline test suite (52) | ✅ |
| NFR-08 | Usability: trilingual + voice | ✅ |
| NFR-09 | Scalability to multi-tenant production load | ❌ SQLite/Streamlit |

---

## 5. Tier mapping (README)

| Tier | Capabilities |
|---|---|
| **1 — Core** | Auth, chat, emergency, booking, medicine, history |
| **2 — Specialist** | Specialist panel, moderator, Rx OCR, related ntfy types |
| **3 — i18n & voice** | EN/SI/TA, STT/TTS, dynamic translation, reminders |

---

## 6. Data requirements

### System-of-record (user-owned)

`User`, `Conversation`, `ChatMessage`, `Appointment`, `Prescription`, `MedicalReport`, `SpecialistOpinion`, `ConsensusReport`, `FutureVisitReminder`, `NotificationLog`

### Marketplace catalog (seed → supplier-published)

`Specialty`, `Facility`, `Doctor`, `AppointmentSlot`, `Medicine`, `Pharmacy`, `PharmacyMedicinePrice`

Schema: `project/db/schema.sql`

---

## 7. Acceptance criteria (prototype)

1. Emergency phrase triggers panel before LLM; confirm shows `tel:1990`.  
2. Booking prompt for seeded full slot shows alternatives table; Book writes atomically.  
3. Medicine query returns sorted pharmacies; complete baskets rank first.  
4. OCR does not run pharmacy lookup until confirm.  
5. Specialist panel shows three opinions; disagreement list non-empty.  
6. App runs usable flows with API key removed (fallbacks).  
7. `pytest` suite green offline (52 tests).  
8. Supplier portal stock toggle visible on patient medicine query.

---

## 8. Future requirements

See [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) Phases 0–3: consent, freshness, RBAC portals, Postgres, FastAPI/React, payments, PDPA export/delete, POS/HIS adapters.
