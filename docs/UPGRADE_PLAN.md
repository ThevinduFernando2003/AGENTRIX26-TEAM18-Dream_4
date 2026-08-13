# MedBridge AI — Full Upgrade & Integration Plan

**Status:** Living upgrade roadmap (derived from codebase + README tiers + `docs/architecture.md` + `docs/DEFENSE.md` + viva guides).  
**Formal specs:** [`SRS.md`](SRS.md) · [`SAD.md`](SAD.md) — this file keeps the gap audit and phased delivery plan.

**Current baseline:** Validated multi-agent **patient prototype** (Streamlit) + **concept supplier portal** (:8502) + SEED marketplace data + 52 offline tests + OpenAI/Gemini provider switch.

---

## 1. Reconstructed SRS (Software Requirements Specification)

### 1.1 Product goal

MedBridge AI helps Sri Lankan patients **navigate** care — specialty triage, emergency guidance, booking, medicine price/stock comparison, prescription OCR, and multi-specialist report review — **without diagnosing**. In production it becomes a **two-sided platform**: hospitals and pharmacies publish slots/prices/stock into MedBridge.

### 1.2 Stakeholders & goals

| Stakeholder | Primary goals |
|---|---|
| **Patient / caregiver** | Know who to see, book safely, find affordable medicine, understand reports, get help in EN/SI/TA, alert family in emergencies |
| **Family contact** | Receive timely emergency / booking / reminder alerts |
| **Hospital / clinic** | Publish doctors & slots; receive reliable bookings; reduce no-shows |
| **Pharmacy** | Publish prices & stock; get foot traffic from searching patients |
| **Platform admin / ops** | Users, content, compliance (PDPA), monitoring, support |
| **Clinical safety / legal** | No diagnosis claims; audit trails; human confirmation on high-risk AI outputs |

### 1.3 Functional requirements (FR) — current vs target

| ID | Requirement | Now | Target |
|---|---|---|---|
| FR-01 | Signup / login with hashed passwords | ✅ Demo-grade | Signed sessions / JWT, MFA optional, rate limit |
| FR-02 | Multi-thread chat with history | ✅ | Same + sync across devices (API) |
| FR-03 | Emergency screen before LLM; confirm; `tel:1990` | ✅ Regex | Multi-hotline map (1990/119/1926) + geo nearest |
| FR-04 | Family emergency / booking alerts | ⚠️ ntfy topic | SMS/WhatsApp/FCM to real phone; authenticated topics |
| FR-05 | Symptom → specialty navigation (not diagnosis) | ✅ RAG + disclaimer | Evaluated retrieval quality; clinician-reviewed KB |
| FR-06 | Book doctor; alternatives if slot full; atomic write | ✅ Seed slots | Live hospital-published slots; calendar sync |
| FR-07 | Medicine price + distance + stock compare | ✅ Seed prices | Live pharmacy updates; freshness labels |
| FR-08 | Prescription OCR + human confirm gate | ✅ | Higher OCR accuracy; multi-page Rx; drug interaction warn (careful scope) |
| FR-09 | 3-specialist panel + moderator disagreement | ✅ | Optional more specialties; clinician review workflow |
| FR-10 | EN / Sinhala / Tamil UI + voice I/O | ✅ | Broader catalog coverage; offline TTS option |
| FR-11 | Future-visit reminders | ⚠️ Manual fire | Background scheduler + push/SMS |
| FR-12 | Pharmacy publishes prices/stock | ⚠️ Concept portal | Merchant accounts, RBAC, POS adapters |
| FR-13 | Hospital publishes slots | ⚠️ Concept portal | Hospital admin accounts, slot templates, cancel/reschedule |
| FR-14 | Payments for channeling fee | ❌ Display only | Checkout gateway + receipts |
| FR-15 | Admin console | ❌ | Users, facilities, audit, feature flags |
| FR-16 | Patient history timeline | ✅ Read-only panel | Richer medical timeline + export (PDPA) |

### 1.4 Non-functional requirements (NFR)

| ID | NFR | Now | Target |
|---|---|---|---|
| NFR-01 | Safety: never diagnose; UI disclaimers | ✅ | Legal review + versioned disclaimer policy |
| NFR-02 | Reliability: LLM down → fallbacks | ✅ | SLOs, circuit breakers, status page |
| NFR-03 | Performance: heuristic domain routes fast | ✅ | p95 API < 3s for booking/medicine without LLM |
| NFR-04 | Privacy: PDPA special-category health data | ⚠️ Partial | Consent, encryption, retention, DPA, breach process |
| NFR-05 | Security: bcrypt; scoped queries | ⚠️ Demo auth | JWT, RBAC, TLS, secrets mgmt, rate limits |
| NFR-06 | Cost: free-tier hackathon constraint | ✅ | Paid LLM + self-host embeddings options |
| NFR-07 | Maintainability: panel contract + tests | ✅ 52 tests | CI, coverage gates, typed API |
| NFR-08 | Usability: trilingual + voice | ✅ | Accessibility (WCAG), mobile-first UX |
| NFR-09 | Scalability | ❌ SQLite/Streamlit | Postgres + FastAPI + horizontal workers |

### 1.5 Constraints & assumptions (from competition + defense docs)

- Sri Lanka has **no open** public pharmacy-stock / channeling APIs → marketplace model is correct.
- Prototype must not pretend live hospital/pharmacy feeds.
- Safety is **structural** (code), not prompt-only.
- SEED data must stay labeled until real suppliers onboard.

---

## 2. Reconstructed SAD (Software Architecture Document)

### 2.1 Current architecture (as-built)

```
Browser / ntfy phone / tel:1990
        │
        ▼
Streamlit Presentation  (project/ui/app.py + panels)     [:8501]
Supplier Portal concept (project/ui/supplier_portal.py)  [:8502]
        │  route_request / pending_* session signals
        ▼
Agent layer (chatbot, emergency, booking, medicine, panel, OCR, reminders)
        │
        ├── llm.py  (Gemini | OpenAI)
        ├── RAG     (Chroma + local ONNX)
        └── SQLite  (17 tables) + kb/ seed JSON
```

**Key patterns:** thin shell / fat panels · heuristic-first routing · typed Pydantic contracts · atomic booking · offline-safe retrieve · provider-agnostic LLM.

### 2.2 Target architecture (production)

```
Mobile / Web (React)          Hospital Admin SPA         Pharmacy Merchant SPA
        │                              │                          │
        └──────────────┬───────────────┴──────────────┬───────────┘
                       ▼                              ▼
                 API Gateway (TLS, auth, rate limit)
                       ▼
              FastAPI / Nest-style backend
         ┌─────────────┼─────────────┬──────────────┐
         ▼             ▼             ▼              ▼
    Agent workers   Booking svc   Catalog svc   Notify svc
    (queue)         (atomic)      (suppliers)   (FCM/SMS)
         │             │             │              │
         └─────────────┴──────┬──────┴──────────────┘
                              ▼
                    Postgres (+ object storage for Rx images)
                    Vector DB (pgvector / managed Chroma)
                              ▼
                    Observability · Audit · Consent store
```

**Migration principle:** keep agent/tool contracts; swap only presentation + data store + auth. Documented in `docs/DEFENSE.md`.

---

## 3. What is working / not working / partial (audit)

### 3.1 Working well ✅

| Area | Evidence |
|---|---|
| Emergency regex before LLM + confirm + 1990 | `agents/emergency.py`, panel |
| Booking alternatives + atomic book + success card | `booking_agent.py`, `panels/booking.py` |
| Booking enrich from raw text (table appears) | `enrich_extracted()` |
| Medicine compare + complete-basket sort | `medicine_tracker.py` |
| Specialist panel + disagreement guard | `specialist_panel.py`, `moderator.py` |
| OCR confirm gate | `prescription.py` |
| Auth bcrypt + session wipe | `auth.py` |
| i18n EN/SI/TA + TTS/STT paths | `i18n/` |
| Offline RAG + graceful LLM degradation | `rag/`, `llm.py` |
| Seed + supplier portal write same tables | `supplier_portal.py` |
| Offline tests | **52 collected** |

### 3.2 Partial / fragile ⚠️

| Issue | Impact | Refine |
|---|---|---|
| Family phone stored but push uses ntfy topic | Families without app miss alerts | SMS/WhatsApp/FCM to phone |
| Reminders need manual “Check reminders” | Easy to miss | Background job / cron worker |
| Supplier portal: no real auth/RBAC | Not production-safe | Merchant + hospital accounts |
| `?uid=` unsigned remember-me | Session hijack risk | Signed cookies / JWT |
| Seed catalogs labeled but UX still “demo” | Trust | Freshness badges, “call to confirm” |
| Chat docs still say “CrewAI orchestrator” in places | Viva/doc drift | Align README/docstrings |
| Voice/OCR depend on quota & network | Demo flakes | Caching, retry UX, offline paste path highlighted |
| Haversine distance ≠ road distance | Ranking imperfect | Maps API later |
| Streamlit UX not mobile-native | Hard for rural users | React/mobile client |
| SQLite single-writer | Won’t scale | Postgres |

### 3.3 Not working / missing ❌

| Gap | Stakeholder hurt |
|---|---|
| No payments / refunds / receipts | Patient, hospital |
| No hospital staff product (roster, cancel, no-show) | Hospital |
| No pharmacy POS sync / bulk upload | Pharmacy |
| No admin/ops console | Platform |
| No CI/CD / Docker in repo | Engineering |
| No live data feeds | All |
| No appointment reschedule/cancel patient flow | Patient |
| No insurance / claim assist | Patient |
| No multi-facility wait-time / queue | Patient, hospital |
| No formal consent & data-export (PDPA) | Legal, patient |
| No rate limiting / abuse protection | Platform |

---

## 4. Features to refine (improve existing)

Priority: **P0** must fix before wider pilot · **P1** next sprint · **P2** later.

### Patient experience

| Item | Priority | Plan |
|---|---|---|
| Clearer empty states & “what can I ask?” chips | P0 | Chat quick prompts always visible |
| Booking: show multi-slot table (already added) + cancel/reschedule | P0/P1 | Add `cancel_appointment`, status transitions |
| Medicine: “updated X hours ago” + call-to-confirm CTA | P0 | Timestamp on `PharmacyMedicinePrice` |
| Emergency: post-confirm checklist (stay calm, don’t drive alone) | P1 | Copy in emergency panel |
| Report panel: progress UI while 3 agents run | P0 | Per-specialist spinner/status |
| OCR: confidence highlights + “edit required fields” | P1 | Mark low-confidence tokens |
| Reminders: auto-fire due jobs | P0 | Worker process / APScheduler |
| History: filter by domain + export PDF | P2 | History panel upgrade |
| Accessibility & mobile layout | P1 | Larger tap targets; reduce scroll |

### Trust & safety

| Item | Priority | Plan |
|---|---|---|
| Align all docs with heuristic-first router | P0 | README + chatbot docstring |
| Versioned medical disclaimer | P1 | Config + audit log |
| Consent at signup (health data processing) | P0 | Checkbox + stored consent record |
| Redact PII from LLM logs | P0 | Logging policy |
| Prompt-injection / jailbreak tests for chat | P1 | Security test suite |

### Engineering hygiene

| Item | Priority | Plan |
|---|---|---|
| CI: pytest on PR | P0 | GitHub Actions |
| Docker Compose (app + postgres later) | P1 | `Dockerfile` |
| Fix remaining doc drift (Tier 3 “out of scope”) | P0 | `project/README.md` |
| Typed OpenAPI when FastAPI lands | P1 | Contract tests |
| Retrieval evaluation set | P1 | Golden questions for RAG |

---

## 5. Features to add (by side) — full integration vision

### 5.1 Patient / client side

1. **Mobile-first web app** (React/PWA) — book, chat, Rx upload from phone camera  
2. **My appointments** — upcoming, cancel, reschedule, directions  
3. **My prescriptions** — history of confirmed OCR + preferred pharmacy  
4. **Care circle** — invite family with verified phone (OTP)  
5. **Payments** — channeling fee pay / hold / refund  
6. **Personal health profile** — allergies, chronic meds (user-entered only)  
7. **Nearest emergency guidance** — Suwa Seriya + hospital ED list by city  
8. **Offline-lite mode** — cached last bookings + emergency numbers without LLM  

### 5.2 Hospital / clinic side

1. **Hospital Admin portal** (replace concept tab)  
   - Org account, facilities, doctor profiles  
   - Weekly slot templates → generate `AppointmentSlot`s  
   - Accept / reject / mark no-show  
   - Conflict rules & buffer times  
2. **Receptionist console** — today’s list, check-in  
3. **Doctor micro-view** — today’s channeling queue (read-only first)  
4. **Analytics** — fill rate, specialty demand (no patient PHI in public charts)  
5. **Optional HL7/FHIR / HIS adapter later** — never block MVP on this  

### 5.3 Pharmacy side

1. **Merchant portal** (harden `:8502`)  
   - Login per pharmacy / chain branch  
   - Bulk CSV upload of prices  
   - One-tap stock toggle  
   - Freshness (“updated 2h ago”)  
2. **POS / ERP adapters** (phase 2) — sync stock from major chains  
3. **“Reserve for pickup”** optional hold (no payment first; then pay)  
4. **Crowdsourced “I bought here today”** signals for cold start  

### 5.4 Family / caregiver side

1. OTP-linked family contacts  
2. Channel preference: ntfy → SMS → WhatsApp Business → FCM  
3. Quiet hours + severity routing (emergency always breaks through)  

### 5.5 Platform admin

1. Admin console: users, facilities, pharmacies, seed vs live flags  
2. Content: symptom→specialty KB editor with review  
3. Audit: NotificationLog, booking log, consent log  
4. Feature flags & kill switches for LLM features  
5. PDPA: export/delete user data workflows  

---

## 6. Phased upgrade plan (how to update)

### Phase 0 — Stabilize prototype (1–2 weeks) · *keep Streamlit*

**Goals:** Trustworthy demo for pilots & CV; no architecture rewrite yet.

- [ ] Doc hygiene: fix CrewAI/chat drift; Tier-3 scope line; test count consistent  
- [ ] Consent checkbox + store timestamp  
- [ ] Medicine freshness timestamp field + UI badge  
- [ ] Reminder background job (simple loop / cron)  
- [ ] Appointment cancel from history  
- [ ] GitHub Actions: `pytest` on push  
- [ ] Supplier portal: basic passcode + “which pharmacy” session binding  
- [ ] Manual regression script = `docs/DEMO_STEPS_UPDATED.md` green  

**Exit:** Pilot-ready prototype with clearer trust labels.

### Phase 1 — Two-sided MVP (4–8 weeks) · *still can keep Streamlit or start FastAPI*

**Goals:** Real hospital + pharmacy users (small pilot), not seed-only.

| Workstream | Deliverables |
|---|---|
| Auth | Roles: `patient`, `pharmacy_staff`, `hospital_staff`, `admin`; JWT or signed sessions |
| Hospital portal | Slot templates, publish, view bookings |
| Pharmacy portal | Price/stock CRUD, CSV import, freshness |
| Patient | My Appointments; pharmacy freshness; family OTP |
| Data | Migrate SQLite → Postgres; keep tool interfaces |
| Notify | Keep ntfy for demo; add SMS gateway for emergency |
| Tests | Expand booking/pharmacy/hospital API tests |

**Pilot suggestion:** 1 hospital OPD + 1 pharmacy chain branch + 50 patients.

### Phase 2 — Product hardening (2–3 months)

- FastAPI backend + React/PWA frontend (swap Streamlit presentation layer)  
- Payments for channeling  
- FCM push + WhatsApp optional  
- Maps road distance  
- Rate limits, lockout, encryption at rest  
- Retrieval evaluation + clinician-reviewed KB  
- Docker + staging + production environments  
- PDPA pack: DPA, retention, breach runbook  

### Phase 3 — Scale & integrations (ongoing)

- POS adapters; HIS/channeling partnerships if opened  
- Multi-city coverage; Osu Sala / chain onboarding  
- Advanced analytics; wait-time estimates  
- Optional insurance workflows  
- Multi-hotline emergency router  

---

## 7. Integration blueprint (how sides connect)

```
Patient books slot ──► Appointment (system of record)
                         ▲
Hospital publishes ──────┘  AppointmentSlot

Patient searches drug ──► quotes_for()
                         ▲
Pharmacy publishes ──────┘  PharmacyMedicinePrice

Patient emergency ──► regex ──► tel:1990 + Notify(family)
Patient OCR confirm ──► pharmacy quotes (same path)
Report panel done ──► Notify(patient topic)
```

**Invariant to preserve in every upgrade:**  
Agents call **typed tools**, never scrape HTML. Replacing seed with portal/POS is a data-layer swap only.

---

## 8. Full test plan (update + verify)

### 8.1 Automated (CI)

| Suite | Scope |
|---|---|
| Unit | emergency patterns, enrich_extracted, medicine match, JSON util, reminders detect |
| Integration | book atomicity, slot UNIQUE, seed idempotent, ntfy log, RAG safe empty |
| Contract | LLM provider returns fallback on bad key |
| Regression | Full `pytest` (maintain ≥52, grow with features) |
| New | Role authz matrix; cancel appointment; freshness sort; CSV pharmacy import |

### 8.2 Manual / UAT by stakeholder

**Patient**

1. Signup + consent → login  
2. Emergency confirm → dial + family alert  
3. Book conflict → table → book → success → appear in My Appointments  
4. Cancel appointment  
5. Medicine basket sort + freshness badge  
6. OCR confirm gate  
7. Report panel disagreement visible  
8. SI/TA language smoke  
9. Reminder auto-fire within window  

**Hospital**

1. Staff login → publish slots for Dr X  
2. Patient books → appears on hospital list  
3. Mark no-show / complete  
4. Duplicate slot rejected cleanly  

**Pharmacy**

1. Staff login → toggle stock / edit price  
2. CSV upload  
3. Patient query reflects update < 1 min  
4. Out-of-stock hidden or badged  

**Admin**

1. Disable LLM feature flag → fallbacks still work  
2. Export/delete user data  
3. Audit log search  

### 8.3 Safety / compliance tests

- No disease diagnosis language in golden prompts  
- OCR never triggers pharmacy before confirm  
- Moderator disagreement never empty  
- Booking never trusts LLM `status=booked` without `book()`  
- Unauthorized role cannot edit another pharmacy’s prices  

---

## 9. Suggested backlog (ready to ticket)

### Epic A — Trust & polish (Phase 0)
1. Doc drift cleanup  
2. Consent + disclaimer versioning  
3. Freshness badges  
4. Reminder worker  
5. Cancel appointment  
6. CI pytest  

### Epic B — Supplier reality (Phase 1)
7. RBAC + org accounts  
8. Hospital slot templates  
9. Pharmacy CSV + portal auth  
10. Family OTP + SMS emergency  

### Epic C — Platform (Phase 2)
11. Postgres migration  
12. FastAPI + React shell  
13. Payments  
14. Docker/staging  
15. PDPA export/delete  

### Epic D — Scale (Phase 3)
16. POS adapter pilot  
17. Maps distance  
18. Multi-hotline emergency  
19. Retrieval eval + KB governance  

---

## 10. Success metrics (client / business)

| Metric | Prototype today | Pilot target |
|---|---|---|
| Time to book alternative slot | Demo minutes | < 2 min median |
| Pharmacy quote freshness | Seed / manual | < 24h for pilot shops |
| Emergency alert delivery | ntfy if subscribed | > 95% SMS/FCM success |
| Booking double-book rate | 0 (UNIQUE) | Keep 0 |
| % sessions with disclaimer seen | High | 100% on clinical surfaces |
| Supplier active weekly | 0 real | ≥ 1 hospital + 1 pharmacy |

---

## 11. Risks & decisions

| Risk | Mitigation |
|---|---|
| No open APIs → cold start | Free supplier tools + one anchor chain / hospital |
| Health data liability | Navigator framing + PDPA + human gates |
| LLM cost / quota | Heuristic-first; cache; local embeddings |
| Streamlit lock-in | Keep agents UI-agnostic (already mostly true) |
| Scope creep into “AI doctor” | Explicit non-goals in SRS; refuse diagnosis features |

**Non-goals (do not build):** automated diagnosis, autonomous prescribing, unverified live stock without supplier accountability.

---

## 12. Immediate next 10 actions (start here)

1. Fix `project/README.md` Tier-3 “out of scope” contradiction.  
2. Align chatbot/README “CrewAI orchestrator” wording with heuristic-first reality.  
3. Add `consent_accepted_at` on User + signup checkbox.  
4. Add `updated_at` on `PharmacyMedicinePrice` + UI badge.  
5. Implement appointment cancel in patient history.  
6. Add APScheduler/cron for due reminders.  
7. Bind supplier portal to pharmacy/hospital login (even simple).  
8. Add GitHub Actions pytest workflow.  
9. Write thin `docs/SRS.md` + `docs/SAD.md` from Sections 1–2 of this plan (formalize).  
10. Run full UAT checklist (§8.2) and log defects in a living `TRIAGE.md`.  

---

## 13. Document map (source of truth today)

| Need | Read |
|---|---|
| Architecture diagrams | `docs/architecture.md` |
| Defense / production path | `docs/DEFENSE.md` |
| Feature tiers | `Readme.md`, `project/README.md` |
| Code paths | `docs/CODEBASE_EXPLANATION.md` |
| Demo verification | `docs/DEMO_STEPS_UPDATED.md` |
| This upgrade plan | `docs/UPGRADE_PLAN.md` (this file) |

---

**Summary:** MedBridge is a strong **patient-side multi-agent prototype** with a proven **publish seam** for hospitals/pharmacies. The upgrade path is not “add more LLM magic” — it is **formalize SRS/SAD → harden trust → make suppliers real → swap Streamlit for API+mobile → payments & PDPA → scale integrations**, while preserving structural safety and typed tool boundaries.
