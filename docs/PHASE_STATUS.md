# MedBridge AI — Phase delivery status

**Branch:** `booking` · **Remote publish:** `origin` only (`ThevinduFernando2003/AGENTRIX26-TEAM18-Dream_4`)  
**As of:** 2026-08-13 · **Offline tests collected:** 85  

---

## Phase 0 — Stabilize (Initial 10) · DONE

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Consent at signup | Done | `User.consent_accepted_at` |
| 2 | Pharmacy freshness badges | Done | `updated_at` + medicine UI column |
| 3 | Cancel appointment | Done | `booking_agent.cancel` + My Appointments |
| 4 | Reminder worker | Done | `python -m project.workers.reminder_worker` |
| 5 | Supplier login + org bind | Done | Unified into `User` roles (Phase 1.1) |
| 6 | CI pytest | Done | `.github/workflows/ci.yml` + GoogleModel fix |
| 7 | Formal SRS/SAD | Done | `docs/SRS.md`, `docs/SAD.md` |
| 8 | UAT checklist | Done | `docs/UAT_CHECKLIST.md` (execute manually) |
| 9 | Doc cleanup | Done | This refresh + project README align |
| 10 | Structural safety | Ongoing | `docs/SAFETY_CHECKLIST.md` every PR |

---

## Phase 1 — Two-sided MVP kickoff · DONE (1.1–1.7)

| Step | Item | Status |
|---|---|---|
| 1.1 | Unified RBAC (`patient` / `pharmacy_staff` / `hospital_staff` / `admin`) | Done |
| 1.2 | Hospital: today’s bookings, no-show, slot templates | Done |
| 1.3 | Pharmacy CSV import (org-scoped) | Done |
| 1.4 | Patient reschedule | Done |
| 1.5 | DB repository seam (`project/db/repo.py`) | Done |
| 1.6 | Optional Postgres via `DATABASE_URL` | Done (CI stays SQLite) |
| 1.7 | Emergency SMS adapter (`stub` / `http`) + ntfy | Done |

**Still open for a real pilot (not blocking code kickoff):** family OTP verification, JWT sessions, live Postgres staging UAT, real SMS gateway credentials, Vercel/React (Phase 2).

---

## Hosting note

Current stack is **Streamlit** (patient `:8501`, supplier `:8502`).  
- **Render / Streamlit Cloud:** feasible for the whole app.  
- **Vercel frontend + Render API:** needs Phase 2 FastAPI + React.  
See [`DEPLOY_RENDER.md`](DEPLOY_RENDER.md).

---

## Demo accounts (SEED)

| App | Username | Password | Role |
|---|---|---|---|
| Patient | `demo1` | `demo1pass` | patient |
| Patient | `demo3` | (see seed) | patient (SI) |
| Supplier | `union` | `unionpass` | pharmacy_staff |
| Supplier | `nawaloka` | `nawalokapass` | hospital_staff |
