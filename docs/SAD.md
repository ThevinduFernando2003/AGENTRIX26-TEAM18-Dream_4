# MedBridge AI — Software Architecture Document (SAD)

**Project:** MedBridge AI · AgenTrix 2026 · Team Dream_4 (TEAM18)  
**Version:** 1.3  
**Status:** As-built includes Phase 0 + Phase 1.1–1.7 on Streamlit; see [`PHASE_STATUS.md`](PHASE_STATUS.md)  
**Related:** [`SRS.md`](SRS.md) · [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) · [`PHASE_STATUS.md`](PHASE_STATUS.md) · [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md) · [`architecture.md`](architecture.md)

---

## 1. Introduction

### 1.1 Purpose

Describe **how** MedBridge is structured today and how it evolves through Phases 0–3 without breaking structural safety or the typed-tool data seam.

### 1.2 Architectural goals

1. Structural safety over prompt trust (**non-negotiable**)  
2. Graceful degradation when LLM/network fails  
3. Two-sided platform: suppliers publish **in**; agents never scrape  
4. Presentation swappable (Streamlit → FastAPI/React) without rewriting agents  
5. Parallel ownership via panel contract  

### 1.3 Stakeholder integration (architecture invariant)

```
Patient books / searches
        │
        ▼
   Typed tools (find_doctors, book, quotes_for, retrieve, …)
        │
        ▼
   Shared system-of-record + catalog tables (SQLite → Postgres)
        ▲
        │
Hospital publishes slots · Pharmacy publishes prices/stock
```

Same tables whether rows come from seed, supplier portal, or future POS/HIS adapters.

---

## 2. As-built architecture (baseline)

### 2.1 Six layers

```
CLIENT         Browser · ntfy phone · tel:1990
PRESENTATION   Streamlit panels :8501 · supplier portal :8502
AGENTS         chatbot · emergency · booking · medicine ·
               panel · moderator · OCR · reminders
INTELLIGENCE   llm.py (Gemini|OpenAI) · RAG (Chroma/ONNX)
DATA           SQLite 17 tables · kb/ seed JSON
EXTERNAL       LLM APIs · ntfy.sh · gTTS
```

Detail diagrams: [`architecture.md`](architecture.md).

### 2.2 Critical components

| Layer | Path | Role |
|---|---|---|
| Shell | `project/ui/app.py` | Auth gate, panel order |
| Portal | `project/ui/supplier_portal.py` | Concept publish |
| Panels | `project/ui/panels/*` | `render(user)`; session signals |
| Router | `project/agents/basic_chatbot.py` | Heuristic-first + timed LLM |
| Safety | `project/agents/emergency.py` | Regex before any LLM |
| Booking | `project/agents/booking_agent.py` | Enrich + tools + atomic book |
| LLM façade | `project/llm.py` | Provider switch, fail-soft |
| Contracts | `project/models.py` | Pydantic models |
| Schema | `project/db/schema.sql` | 17 tables |

### 2.3 Connectors

| From → To | Mechanism |
|---|---|
| Chat → domain | `route_request` session signal |
| Domain → agents | Direct import in owning panel |
| Agents → data | SQL via `get_conn()` / typed tools |
| Agents → LLM | `project.llm` only |
| Agents → vectors | `rag.retriever.retrieve` |
| Alerts → family | ntfy + `NotificationLog` |

### 2.4 Safety architecture (must not regress)

| Control | Enforcement |
|---|---|
| Emergency first | Regex before LLM/network |
| No hallucinated booking | Only `book()` writes; LLM proposes |
| OCR gate | Confirm before pharmacy lookup |
| Dosage | Catalog `reference_dosage_text` only |
| Disagreement visible | Moderator invariant |
| No diagnosis | UI disclaimer + specialty navigation only |
| Offline-safe RAG | `retrieve()` returns `[]`, never raises |

---

## 3. Target architecture by phase

### Phase 0 — Stabilize (keep Streamlit/SQLite) · **delivered**

- `User.consent_accepted_at`  
- `PharmacyMedicinePrice.updated_at` + UI badge  
- `cancel` + My Appointments panel  
- Reminder worker (`project/workers/reminder_worker.py`)  
- Supplier portal login (now unified `User` roles)  
- GitHub Actions → `pytest`  
- Doc alignment with heuristic-first router  

### Phase 1 — Two-sided MVP · **kickoff delivered (1.1–1.7)**

```
Patient UI (Streamlit)
Hospital portal ──┐
Pharmacy portal ──┼──► authz.py (RBAC) ──► services ──► SQLite | Postgres(DATABASE_URL)
                  │                         │
                  │                         ├── booking_agent (atomic book/cancel/reschedule)
                  │                         ├── hospital_service / pharmacy_service
                  │                         ├── db/repo.py seam
                  │                         └── notify (ntfy + SMS stub/http)
```

Roles on `User.role`: `patient` · `hospital_staff` · `pharmacy_staff` · `admin`.  
Staff seed: `union` / `nawaloka` (see `seed_suppliers.json`).  
Remaining for full pilot: family OTP, JWT, staging Postgres UAT, real SMS gateway.

### Phase 2 — Product platform

```
React/PWA · Hospital SPA · Pharmacy SPA
            │
     API Gateway (TLS, JWT, rate limit)
            │
         FastAPI
     workers · payments · FCM
            │
     Postgres + object storage + vector index
            │
     Observability · Consent store · PDPA tools
```

### Phase 3 — Scale & external systems

- POS adapters → `PharmacyMedicinePrice`  
- Optional HIS/channeling adapters → `AppointmentSlot`  
- Maps distance service  
- Multi-hotline emergency dictionary  
- Multi-city onboarding  

---

## 4. Data architecture

### 4.1 Table groups

**System of record:** User, Conversation, ChatMessage, Appointment, Prescription, MedicalReport, SpecialistOpinion, ConsensusReport, FutureVisitReminder, NotificationLog (+ consent fields).

**Marketplace catalog:** Specialty, Facility, Doctor, AppointmentSlot, Medicine, Pharmacy, PharmacyMedicinePrice (+ `updated_at`).

### 4.2 Migration principle

Tool signatures (`find_doctors`, `nearest_alternatives`, `book`, `quotes_for`, `retrieve`) stay stable. Swap SQLite→Postgres behind `get_conn()` / repository layer.

---

## 5. Deployment architecture

| Stage | Topology |
|---|---|
| Now | Local Streamlit ×2, SQLite file, optional Cloud secrets |
| P0 | Same + CI; reminder worker as second process |
| P1 | Postgres (managed); Streamlit or early API |
| P2 | Containerized API + web + worker + staging/prod |
| P3 | Adapters as separate services/jobs |

---

## 6. Security architecture evolution

| Concern | Now | P0 | P1 | P2 |
|---|---|---|---|---|
| Passwords | bcrypt | bcrypt | + lockout | + argon2 option |
| Sessions | Streamlit / `?uid=` | document risk | JWT/signed | same + refresh |
| Supplier access | optional passcode | required bind | RBAC | RBAC + audit |
| Consent | none | timestamp | versioned policy | export/delete |
| Push | ntfy | ntfy | + SMS emergency | FCM/WhatsApp |

---

## 7. Quality & test architecture

| Layer | Practice |
|---|---|
| Unit | emergency, enrich, match, reminders |
| Integration | atomic book, seed, ntfy log, RAG safe |
| CI (P0) | GitHub Actions `pytest -q` |
| UAT | Stakeholder checklists in IMPLEMENTATION_PLAN |
| Safety regression | Never skip: emergency-first, OCR gate, book atomicity, disagreement guard |

---

## 8. ADR summary

| Decision | Why |
|---|---|
| Streamlit first | Speed, Python-only, panel parallelization |
| Heuristic-first chat | Avoid LLM latency/429 on clear intents |
| CrewAI only for panel | Parallel role independence |
| Pydantic AI booking | Typed SQL tools |
| Own catalogs | No open APIs; platform is SoR |
| Local ONNX RAG | Offline, free, stable dims |
| Phase LLM UI swap late | Validate marketplace + safety first |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Scope creep → diagnosis features | SRS non-goals; safety checklist in PR template |
| Supplier cold start | Free portals + 1+1 pilot (Phase 1) |
| Streamlit lock-in | Agents UI-agnostic; Phase 2 swap |
| Doc/code drift | SRS/SAD/IMPLEMENTATION_PLAN living; P0 doc cleanup |
| Health-data liability | Navigator framing + PDPA phases |

---

## 10. Traceability to delivery

| Phase | Architecture change | Spec |
|---|---|---|
| 0 | Additive fields, worker, CI, portal bind | SRS Initial 10 |
| 1 | RBAC, Postgres, real portals, SMS | SRS FR-H/PH/F |
| 2 | FastAPI/React, payments, FCM, PDPA | SRS FR-P16, FR-A*, NFR-07/08 |
| 3 | POS/HIS, Maps, multi-hotline | SRS FR-X04/05, FR-H04, FR-PH04 |

Execution detail: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).
