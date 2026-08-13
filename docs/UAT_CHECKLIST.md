# MedBridge AI — UAT Checklist

**Use at:** end of Phase 0 / Phase 1 kickoff, and every later phase exit.  
**Related:** [`PHASE_STATUS.md`](PHASE_STATUS.md) · [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) · [`DEMO_STEPS_UPDATED.md`](DEMO_STEPS_UPDATED.md) · [`SRS.md`](SRS.md)

**Build / commit:** _______________  
**Tester:** _______________  
**Date:** _______________  

---

## A. Patient (client)

| # | Case | Pass? | Notes |
|---|---|---|---|
| A1 | Signup requires consent; timestamp stored | ☐ | |
| A2 | Login `demo1` / `demo1pass` | ☐ | |
| A3 | `hello` → warm LLM or acceptable fallback | ☐ | |
| A4 | Emergency phrase → confirm → `tel:1990` (+ alert) | ☐ | |
| A5 | Book Dr Sunil tomorrow 10:00 → **table** → Book → success | ☐ | |
| A6 | Cancel that appointment → slot free again | ☐ | My appointments |
| A6b | Reschedule to another same-doctor slot | ☐ | Phase 1.4 |
| A7 | Medicine Panadol+Amoxicillin → sort + freshness badge | ☐ | |
| A8 | Portal Losartan in-stock → patient sees update | ☐ | union staff |
| A9 | Report ambiguous sample → 3 opinions + disagreement | ☐ | |
| A10 | Rx OCR → confirm gate → pharmacies | ☐ | |
| A11 | `demo3` reminder / SI smoke | ☐ | |
| A12 | API key removed → core flows still work | ☐ | |
| A13 | Signup without consent blocked | ☐ | |

## B. Hospital side

| # | Case | Pass? | Notes |
|---|---|---|---|
| B1 | Login `nawaloka` / `nawalokapass` required | ☐ | hospital_staff |
| B2 | Publish slot for bound facility only | ☐ | |
| B3 | Duplicate slot rejected cleanly | ☐ | |
| B4 | Today’s bookings lists patient booking | ☐ | Phase 1.2 |
| B5 | Mark no-show | ☐ | |
| B6 | Slot template publishes multiple days | ☐ | |

## C. Pharmacy side

| # | Case | Pass? | Notes |
|---|---|---|---|
| C1 | Login `union` / `unionpass` required | ☐ | pharmacy_staff |
| C2 | Edit price/stock updates `updated_at` | ☐ | |
| C3 | Cannot edit another pharmacy’s rows | ☐ | |
| C4 | CSV import updates bound pharmacy only | ☐ | Phase 1.3 |

## D. Family / notify

| # | Case | Pass? | Notes |
|---|---|---|---|
| D1 | ntfy emergency/booking received if subscribed | ☐ | |
| D2 | Reminder worker `--once` fires due reminder | ☐ | |
| D3 | SMS stub/http fires when family phone set | ☐ | OTP still open |

## E. Safety regression (mandatory)

| # | Case | Pass? | Notes |
|---|---|---|---|
| E1 | Emergency runs before LLM | ☐ | |
| E2 | OCR does not lookup before confirm | ☐ | |
| E3 | LLM cannot create booking without `book()` | ☐ | |
| E4 | Moderator disagreement non-empty | ☐ | |
| E5 | Dosage only from catalog text | ☐ | |
| E6 | Disclaimer visible on clinical surfaces | ☐ | |

## F. Engineering

| # | Case | Pass? | Notes |
|---|---|---|---|
| F1 | `pytest -q` → green (≈85 collected) | ☐ | |
| F2 | GitHub Actions CI green on push | ☐ | Phase 0+ |
| F3 | README matches heuristic-first router | ☐ | |

---

## Sign-off

| Role | Name | Sign | Date |
|---|---|---|---|
| Patient UAT | | ☐ | |
| Hospital UAT | | ☐ | |
| Pharmacy UAT | | ☐ | |
| Safety review | | ☐ | |

**Phase exit decision:** ☐ Pass · ☐ Pass with waivers · ☐ Fail (list blockers below)

Blockers:
1. …
2. …
