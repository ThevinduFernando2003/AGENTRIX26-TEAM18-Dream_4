# MedBridge AI — Software Requirements Specification (SRS)

**Project:** MedBridge AI · AgenTrix 2026 · Team Dream_4 (TEAM18)  
**Version:** 1.3  
**Status:** Authoritative requirements baseline; Phase 0 + Phase 1.1–1.7 implemented on `booking` (see [`PHASE_STATUS.md`](PHASE_STATUS.md))  
**Related:** [`SAD.md`](SAD.md) · [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) · [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) · [`PHASE_STATUS.md`](PHASE_STATUS.md) · [`DEFENSE.md`](DEFENSE.md)

---

## 1. Introduction

### 1.1 Purpose

Define **what** MedBridge AI must do for patients, families, hospitals, pharmacies, and platform operators — separating **as-built prototype** from **production target** — so engineering can execute Phases 0–3 without scope drift into “AI doctor” features.

### 1.2 Product goal

MedBridge is a multi-agent healthcare **navigator** for Sri Lanka: specialty triage, emergency guidance, booking, medicine comparison, prescription OCR, and multi-specialist report review — **never a diagnoser**. Production form is a **two-sided platform**: hospitals and pharmacies publish slots/prices/stock into MedBridge; agents consume data only through typed tools.

### 1.3 In scope / out of scope

| In scope | Out of scope (non-goals) |
|---|---|
| Navigation, logistics, comparison, alerts | Automated diagnosis as clinical truth |
| Two-sided publish model (hospital/pharmacy) | Inventing dosages or autonomous prescribing |
| Structural safety + offline LLM fallbacks | Claiming live feeds without supplier accountability |
| Trilingual UX (EN/SI/TA) + voice | Replacing licensed clinicians |

### 1.4 Stakeholders

| Stakeholder | Goals |
|---|---|
| Patient / caregiver | Right specialty, book, affordable medicine, understand reports, language/voice, emergency help |
| Family contact | Reliable emergency / booking / reminder alerts |
| Hospital / clinic | Publish doctors & slots; receive authoritative bookings; reduce no-shows |
| Pharmacy | Publish prices & stock; foot traffic from searchers |
| Platform admin | Users, content, PDPA, monitoring, feature flags |
| Safety / legal | No diagnosis claims; audit; human gates on high-risk AI |

### 1.5 Assumptions & constraints

1. No open public Sri Lankan channeling or pharmacy-stock APIs → marketplace publish model.  
2. Prototype catalogs may be SEED until real suppliers onboard (must stay labeled).  
3. Safety is enforced in **code**, not prompts alone.  
4. Health data is a special category under Sri Lanka PDPA No. 9 of 2022.  
5. **Structural safety is non-negotiable** across every phase.

---

## 2. Functional requirements

Legend: ✅ as-built · ⚠️ partial · ❌ target

### 2.1 Patient / client

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-P01 | Signup/login with hashed passwords | ✅ | harden P1 |
| FR-P02 | Explicit consent for health-data processing | ✅ | P0 done |
| FR-P03 | Multi-thread chat + history | ✅ | — |
| FR-P04 | Emergency regex before LLM; confirm; `tel:1990` | ✅ | extend P3 |
| FR-P05 | Symptom → specialty (RAG); never diagnose; disclaimer | ✅ | eval P2 |
| FR-P06 | Book doctor; alternatives if full; atomic write | ✅ | — |
| FR-P07 | Visible availability table + Book actions | ✅ | — |
| FR-P08 | Cancel (and later reschedule) appointment | ✅ | P0 cancel · P1 reschedule |
| FR-P09 | Medicine price/stock/distance compare | ✅ | — |
| FR-P10 | Freshness badge on pharmacy prices (“updated X ago”) | ✅ | P0 done |
| FR-P11 | Rx OCR + human confirm before pharmacy lookup | ✅ | — |
| FR-P12 | 3-specialist panel + non-empty disagreement | ✅ | — |
| FR-P13 | EN/SI/TA UI + STT/TTS | ✅ | — |
| FR-P14 | Future-visit reminders auto-delivered when due | ✅ | worker + sidebar override |
| FR-P15 | My Appointments / richer history export | ⚠️ | My Appointments + cancel/reschedule; export later |
| FR-P16 | Pay channeling fee + receipt | ❌ | P2 |

### 2.2 Family

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-F01 | Receive emergency/booking/reminder alerts | ⚠️ | ntfy + SMS stub/http; OTP later |
| FR-F02 | Verified family phone (OTP) | ❌ | P1 remaining |
| FR-F03 | Authenticated push (FCM) / WhatsApp option | ❌ | P2 |

### 2.3 Hospital

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-H01 | Publish appointment slots into platform DB | ✅ | staff portal + templates |
| FR-H02 | Org/staff accounts + RBAC | ✅ | `User.role` + org bind |
| FR-H03 | Slot templates; view/manage bookings; no-show | ✅ | P1.2 |
| FR-H04 | HIS / channeling adapter (optional) | ❌ | P3 |

### 2.4 Pharmacy

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-PH01 | Publish price/stock into shared tables | ✅ | portal CRUD |
| FR-PH02 | Merchant accounts + RBAC | ✅ | `pharmacy_staff` |
| FR-PH03 | CSV bulk upload; freshness timestamps | ✅ | stamp + CSV |
| FR-PH04 | POS / ERP sync adapters | ❌ | P3 |

### 2.5 Platform admin / ops

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-A01 | Admin console (users, facilities, flags) | ❌ | P2 |
| FR-A02 | CI on every push (`pytest`) | ✅ | GitHub Actions |
| FR-A03 | Formal SRS/SAD maintained | ✅ (this doc) | living |
| FR-A04 | UAT checklist executed & logged | ⚠️ | checklist ready; run & sign |
| FR-A05 | PDPA export/delete workflows | ❌ | P2 |
| FR-A06 | Doc drift cleanup (README vs code) | ✅ | Phase status + this refresh |

### 2.6 Cross-cutting intelligence

| ID | Requirement | Now | Phase |
|---|---|---|---|
| FR-X01 | `LLM_PROVIDER` Gemini \| OpenAI | ✅ | — |
| FR-X02 | Deterministic fallbacks when LLM down | ✅ | forever |
| FR-X03 | Agents use typed tools only (no scrape) | ✅ | forever |
| FR-X04 | Road distance (Maps) vs haversine | ❌ | P2–P3 |
| FR-X05 | Multi-hotline emergency routing | ❌ | P3 |

---

## 3. Non-functional requirements

| ID | NFR | Now | Target phase |
|---|---|---|---|
| NFR-01 | **Structural safety non-negotiable** | ✅ | all phases |
| NFR-02 | Graceful degradation without API key | ✅ | all |
| NFR-03 | Heuristic-first domain latency | ✅ | all |
| NFR-04 | PDPA-aligned privacy | ⚠️ | consent done · P2 pack |
| NFR-05 | AuthN/AuthZ production-grade | ⚠️ | RBAC roles done · JWT later |
| NFR-06 | Offline test suite ≥52, CI green | ✅ | ~85 tests · Actions |
| NFR-07 | Scalability beyond single SQLite writer | ⚠️ | `DATABASE_URL` Postgres optional · P2 API |
| NFR-08 | Mobile-first usable UX | ⚠️ Streamlit | P2 React/PWA |
| NFR-09 | Observability (logs, audit, kill switches) | ⚠️ NotificationLog | P2 |

---

## 4. Initial 10 work items (SRS → delivery)

| # | Work item | Primary FR/NFR | Phase |
|---|---|---|---|
| 1 | Consent capture at signup | FR-P02, NFR-04 | P0 |
| 2 | Pharmacy freshness badges | FR-P10, FR-PH03 | P0 |
| 3 | Cancel appointment | FR-P08 | P0 |
| 4 | Reminder cron / worker | FR-P14 | P0 |
| 5 | Supplier login (pharmacy/hospital bind) | FR-H01, FR-PH01 | P0 |
| 6 | CI pytest (GitHub Actions) | FR-A02, NFR-06 | P0 |
| 7 | Formalize SRS + SAD | FR-A03 | P0 ✅ |
| 8 | UAT checklist | FR-A04 | P0 |
| 9 | Doc cleanup (drift) | FR-A06 | P0 |
| 10 | Keep structural safety non-negotiable | NFR-01 | all |

Detailed tasks: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

---

## 5. Acceptance criteria (prototype + Phase 0 exit)

1. Emergency before LLM; confirm → `tel:1990`.  
2. Booking conflict → alternatives **table** → atomic Book.  
3. Medicine sort: complete baskets first; freshness visible after P0.  
4. OCR never pharmacies before confirm.  
5. Specialist disagreement list never empty.  
6. App usable with API key removed.  
7. `pytest` green offline; CI runs on push after P0.  
8. Signup stores consent timestamp after P0.  
9. Patient can cancel own future appointment after P0.  
10. Due reminders fire without manual button after P0.  
11. Supplier portal requires login/passcode and scopes edits after P0.

---

## 6. Tier mapping (README)

| Tier | Capabilities |
|---|---|
| 1 Core | Auth, chat, emergency, booking, medicine, history |
| 2 Specialist | Panel, moderator, Rx OCR, related ntfy |
| 3 i18n & voice | EN/SI/TA, STT/TTS, translation, reminders |

---

## 7. Traceability

| Need | Document |
|---|---|
| How it is built | [`SAD.md`](SAD.md) |
| How we deliver Phases 0–3 | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) |
| Gap audit narrative | [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) |
| Viva defense | [`DEFENSE.md`](DEFENSE.md) |
