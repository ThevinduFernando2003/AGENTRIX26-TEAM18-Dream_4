# MedBridge AI — Implementation Plan (from SRS + SAD)

**Version:** 1.0  
**Based on:** [`SRS.md`](SRS.md) v1.2 · [`SAD.md`](SAD.md) v1.2  
**Companion gap narrative:** [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md)  
**Rule zero:** Structural safety is non-negotiable (SRS NFR-01 / SAD §2.4). No phase may weaken emergency-first, OCR confirm, atomic booking, or disagreement guards.

---

## 0. Document map

| Doc | Role |
|---|---|
| `docs/SRS.md` | **What** to build (FR/NFR, phases, Initial 10) |
| `docs/SAD.md` | **How** it is structured now and by phase |
| `docs/IMPLEMENTATION_PLAN.md` | **When / who / tasks / tests** (this file) |
| `docs/UPGRADE_PLAN.md` | Long-form audit + backlog |
| `docs/DEMO_STEPS_UPDATED.md` | Manual happy-path regression |
| `docs/UAT_CHECKLIST.md` | Stakeholder UAT (created with this plan) |

---

## 1. Vision & integration model

```
┌─────────────┐     typed tools      ┌──────────────────────────┐
│   Patient   │ ───────────────────► │ Shared DB (SoR+catalog)  │
│  (client)   │ ◄─────────────────── │ User, Appointment, …     │
└─────────────┘     results/alerts   │ Slot, PharmacyPrice, …   │
                                     └────────────▲─────────────┘
                                                  │ publish
                          ┌───────────────────────┴───────────────────────┐
                          │                                               │
                   ┌──────┴──────┐                               ┌────────┴────────┐
                   │  Hospital   │                               │    Pharmacy     │
                   │   portal    │                               │     portal      │
                   └─────────────┘                               └─────────────────┘
```

Agents never scrape third-party HTML. Seed → portal → POS/HIS are interchangeable publishers into the same tables.

---

## 2. Phase overview

| Phase | Duration | Goal | Stack posture |
|---|---|---|---|
| **0 Stabilize** | 1–2 weeks | Trust + ops hygiene; Initial 10 | Keep Streamlit + SQLite |
| **1 Two-sided MVP** | 4–8 weeks | Real hospital + pharmacy pilot | RBAC + Postgres |
| **2 Product platform** | 2–3 months | Mobile/API product | FastAPI + React/PWA |
| **3 Scale** | ongoing | External systems + geography | Adapters + Maps |

---

## 3. Initial 10 — detailed Phase 0 plan

Execute in this order (dependencies respected).

### 1) Consent — FR-P02

| | |
|---|---|
| **Files** | `project/db/schema.sql`, `db.py` migrate, `ui/auth.py`, `i18n/translate.py` |
| **Work** | Add `consent_accepted_at TEXT`; signup checkbox required; block signup without consent; show short PDPA-style notice |
| **Tests** | Signup without consent fails; with consent persists timestamp |
| **Done when** | New users always have non-null consent timestamp |

### 2) Freshness badges — FR-P10 / FR-PH03

| | |
|---|---|
| **Files** | `schema.sql` / migrate `PharmacyMedicinePrice.updated_at`; `seed.py`; `medicine_tracker.py`; `panels/medicine.py`; supplier portal save path |
| **Work** | Set `updated_at` on seed load and every portal edit; show “Updated Xh ago” / “SEED” badge |
| **Tests** | Portal update bumps timestamp; UI column present |
| **Done when** | Patient medicine table shows freshness per pharmacy row |

### 3) Cancel appointment — FR-P08

| | |
|---|---|
| **Files** | `booking_agent.py` (`cancel`), `panels/history.py` or new appointments section, `schema` status values |
| **Work** | Patient cancels own future `confirmed` appointment; free slot (`is_available=1`); optional ntfy |
| **Tests** | Cannot cancel others’; slot reopens; status=`cancelled` |
| **Done when** | Demo user can book then cancel from UI |

### 4) Reminder worker — FR-P14

| | |
|---|---|
| **Files** | `agents/reminders.py`; new `project/workers/reminder_worker.py` (or script); README run instructions |
| **Work** | Process due reminders on interval (APScheduler or loop sleep); keep sidebar button as manual override |
| **Tests** | Due row notified once; idempotent |
| **Done when** | Worker fires demo1 near-due reminder without clicking sidebar |

### 5) Supplier login — FR-H01 / FR-PH01

| | |
|---|---|
| **Files** | `ui/supplier_portal.py`; optional `SupplierAccount` table or env map; session state bind |
| **Work** | Require passcode **or** simple username per pharmacy/facility; edits only for bound org; banner still “concept / SEED” |
| **Tests** | Unauthenticated edit blocked; wrong org cannot update other pharmacy |
| **Done when** | Portal demo uses login then Losartan toggle still works |

### 6) CI pytest — FR-A02

| | |
|---|---|
| **Files** | `.github/workflows/ci.yml`; pin Python; `requirements-dev.txt` |
| **Work** | On push/PR: checkout, install, `pytest -q` |
| **Done when** | Green check on `booking` / `main` push |

### 7) Formalize SRS + SAD — FR-A03

| | |
|---|---|
| **Files** | `docs/SRS.md`, `docs/SAD.md` |
| **Status** | **Done (v1.2)** |
| **Done when** | Linked from README Table of Contents |

### 8) UAT checklist — FR-A04

| | |
|---|---|
| **Files** | `docs/UAT_CHECKLIST.md` (this delivery) |
| **Work** | Patient / hospital / pharmacy / safety checklists; sign-off table |
| **Done when** | One full UAT pass logged after Phase 0 code lands |

### 9) Doc cleanup — FR-A06

| | |
|---|---|
| **Files** | `Readme.md`, `project/README.md`, `basic_chatbot.py` docstring |
| **Work** | Remove “CrewAI orchestrator” for chat; fix Tier-3 “out of scope”; link SRS/SAD/IMPLEMENTATION_PLAN; keep test count = 52 |
| **Done when** | No contradictory chat-routing claims in README |

### 10) Structural safety — NFR-01

| | |
|---|---|
| **Files** | PR checklist in `docs/SAFETY_CHECKLIST.md` (short); CI must keep emergency/booking/OCR/moderator tests |
| **Work** | Explicit non-regression list reviewed every PR |
| **Done when** | Checklist exists and is referenced in CI or CONTRIBUTING blurb |

**Phase 0 exit criteria:** all 10 items done · `pytest` CI green · UAT checklist pass · demo script still ≤12 minutes.

---

## 4. Phase 1 — Two-sided MVP (4–8 weeks)

### Goals
Real (small) hospital + pharmacy users; Postgres; family SMS for emergencies; RBAC.

### Workstreams

| Stream | Deliverables | SRS |
|---|---|---|
| **AuthZ** | Roles: patient, hospital_staff, pharmacy_staff, admin; signed sessions/JWT | FR-P01, FR-H02, FR-PH02 |
| **Hospital portal** | Slot templates, publish, today’s bookings, no-show | FR-H01–H03 |
| **Pharmacy portal** | CRUD + CSV import + freshness (from P0) | FR-PH01–PH03 |
| **Patient** | My Appointments; cancel (P0) + reschedule; family OTP | FR-P08, FR-P15, FR-F02 |
| **Data** | SQLite → Postgres; repository behind `get_conn` | NFR-07 |
| **Notify** | SMS gateway for emergency (keep ntfy for demo) | FR-F01 |
| **Tests** | Authz matrix; portal isolation; migration smoke | — |

### Pilot definition of done
- 1 hospital OPD publishes live slots for ≥1 doctor  
- 1 pharmacy branch updates stock daily  
- ≥20 successful patient bookings without double-book  
- Emergency SMS reaches verified family number in pilot  

### Architecture (SAD Phase 1)
Keep Streamlit **or** introduce minimal FastAPI for portals; **must** introduce Postgres and RBAC.

---

## 5. Phase 2 — Product platform (2–3 months)

| Workstream | Deliverables | SRS |
|---|---|---|
| API + Web | FastAPI + React/PWA; retire Streamlit as primary UX | NFR-08 |
| Payments | Channeling checkout + receipt | FR-P16 |
| Push | FCM (+ optional WhatsApp) | FR-F03 |
| Security | Rate limits, lockout, TLS, encryption at rest | NFR-05 |
| PDPA | Export/delete, retention, breach runbook | FR-A05, NFR-04 |
| Quality | Retrieval eval set; Docker staging/prod | FR-P05, NFR-06 |
| Admin | Feature flags, audit UI | FR-A01 |

### Definition of done
- Staging deploy via Docker Compose/K8s  
- Patient completes book→pay→confirm on PWA  
- PDPA export/delete operable for a test user  

---

## 6. Phase 3 — Scale & integrations (ongoing)

| Workstream | Deliverables | SRS |
|---|---|---|
| POS adapters | Chain stock → `PharmacyMedicinePrice` | FR-PH04 |
| HIS/channeling | Optional slot sync | FR-H04 |
| Maps | Road distance ranking | FR-X04 |
| Emergency | Multi-hotline router (1990/119/1926…) | FR-X05 |
| Growth | Multi-city; Osu Sala / chain onboarding | — |
| Analytics | Fill-rate, demand (privacy-preserving) | — |

---

## 7. Suggested team allocation

| Person | Phase 0 | Phase 1 |
|---|---|---|
| **Janidu** | Doc cleanup, CI, consent UX, safety checklist | RAG eval prep, patient API shell |
| **Thevindu** | Cancel booking, reminder worker | Hospital portal + booking services |
| **Nisal** | Freshness badges + medicine UI | Pharmacy portal + CSV |
| **Chanupa** | Supplier login bind, auth migrations | RBAC + Postgres + notify SMS |

---

## 8. Week-by-week (Phase 0 example)

| Day | Focus |
|---|---|
| 1–2 | Doc cleanup + link SRS/SAD; CI workflow |
| 3–4 | Consent schema + signup UX + tests |
| 5–6 | Freshness column + portal bump + medicine badge |
| 7–8 | Cancel appointment + history UI + tests |
| 9–10 | Reminder worker + supplier login bind |
| 11 | Safety checklist + UAT dry run |
| 12–14 | Buffer, bugfix, full UAT sign-off |

---

## 9. Test strategy (all phases)

### Automated
- Keep existing 52 offline tests green always  
- Add tests per Initial 10 item before merge  
- CI blocks merge on failure (P0+)  

### Safety regression (every PR)
- [ ] Emergency still pre-LLM  
- [ ] OCR still gated  
- [ ] `book()` still only writer; LLM cannot force booked  
- [ ] Moderator disagreement non-empty  
- [ ] Dosage still catalog-only  

### UAT
Run [`UAT_CHECKLIST.md`](UAT_CHECKLIST.md) at Phase 0 exit and every phase exit.

---

## 10. Risks & decisions log

| Risk | Decision |
|---|---|
| Building FastAPI too early | **Defer to Phase 2**; validate suppliers in P1 first |
| SMS cost | Emergency-only in P1; ntfy remains for non-critical |
| Postgres migration pain | Introduce repository seam in P0/P1 before cutover |
| Diagnosis feature requests | Reject per SRS non-goals |

---

## 11. Immediate next actions

Phase 0 Initial 10 and Phase 1.1–1.7 kickoff are implemented on `booking` (push `origin` only).

**Phase 1 remaining / pilot hardening:**
1. Run full UAT checklist against staff portals + reschedule + CSV.  
2. Point a staging Postgres via `DATABASE_URL` and verify seed.  
3. Wire a real SMS HTTP gateway for pilot emergency numbers.  
4. Pilot: 1 hospital OPD + 1 pharmacy branch live publish.

---

## 12. Success metrics

| Metric | Phase 0 | Phase 1 | Phase 2 |
|---|---|---|---|
| CI green | Required | Required | Required |
| Double-book rate | 0 | 0 | 0 |
| Consent coverage (new users) | 100% | 100% | 100% |
| Supplier-authenticated edits | Yes | Yes | Yes |
| Pilot hospitals / pharmacies | 0 | 1 / 1 | N+ |
| PDPA export | — | — | Yes |
