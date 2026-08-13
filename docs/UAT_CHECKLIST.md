# MedBridge AI — UAT Checklist

**Use at:** end of Phase 0, and every later phase exit.  
**Related:** [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) · [`DEMO_STEPS_UPDATED.md`](DEMO_STEPS_UPDATED.md) · [`SRS.md`](SRS.md)

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
| A6 | Cancel that appointment → slot free again | ☐ | Phase 0+ |
| A7 | Medicine Panadol+Amoxicillin → sort + freshness badge | ☐ | |
| A8 | Portal Losartan in-stock → patient sees update | ☐ | |
| A9 | Report ambiguous sample → 3 opinions + disagreement | ☐ | |
| A10 | Rx OCR → confirm gate → pharmacies | ☐ | |
| A11 | `demo3` reminder / SI smoke | ☐ | |
| A12 | API key removed → core flows still work | ☐ | |

## B. Hospital side

| # | Case | Pass? | Notes |
|---|---|---|---|
| B1 | Supplier/hospital login required | ☐ | Phase 0+ |
| B2 | Publish slot for bound facility only | ☐ | |
| B3 | Duplicate slot rejected cleanly | ☐ | |
| B4 | Patient booking appears for hospital (P1) | ☐ | |

## C. Pharmacy side

| # | Case | Pass? | Notes |
|---|---|---|---|
| C1 | Pharmacy login / bind required | ☐ | Phase 0+ |
| C2 | Edit price/stock updates `updated_at` | ☐ | |
| C3 | Cannot edit another pharmacy’s rows | ☐ | |
| C4 | CSV import (P1) | ☐ | |

## D. Family / notify

| # | Case | Pass? | Notes |
|---|---|---|---|
| D1 | ntfy emergency/booking received if subscribed | ☐ | |
| D2 | Reminder worker fires due reminder (P0) | ☐ | |
| D3 | SMS to verified family (P1) | ☐ | |

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
| F1 | `pytest -q` → 52+ green | ☐ | |
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
