# TRIAGE — Phase 0/1 status (Friday)

Scratch file — not for the repo history if you'd rather not commit it.

## ✅ Verified programmatically (fresh DB + fresh RAG index)

| Check | Result |
|---|---|
| Clean boot: seed (6 users, 8 doctors, 43 slots, 5 pharmacies, 50 prices) | ✅ |
| RAG ingest + retrieval ("chest pain" → Cardiology 0.65; "parasetmol" → Paracetamol) | ✅ |
| Emergency regex fires on "severe chest pain / can't breathe" | ✅ |
| Dr. Sunil Perera tomorrow 10:00 seeded full → 5 alternatives | ✅ |
| Medicine quotes with geo → 5 pharmacies, sorted | ✅ (sort fixed, see below) |
| demo1 near-due reminder in 7-day window | ✅ |
| Losartan @ Union Chemists seeded out-of-stock (portal demo moment) | ✅ |
| ntfy test push to `https://ntfy.sh/medbridge-demo-1` | ✅ sent |
| pytest after all edits | ✅ 52/52 |

## 🔧 Fixed in this pass (uncommitted — review with `git diff`)

1. **Booking success bug** — `st.success()` was wiped by its own `st.rerun()`; the user never saw the confirmation. Now a success card renders on the next run with a Dismiss button. (`ui/panels/booking.py`)
2. **Medicine sort** — a pharmacy *missing* an item could rank #1 on partial total (Lanka Hospitals at LKR 15 beat complete baskets). Now: complete baskets first → total → distance. (`agents/medicine_tracker.py`)
3. **Medicine table** — new "Has all?" ✅/⚠️ column, `LKR` formatting, `x.x km`, every row carries every column (no misalignment), missing shown as "—" when none. (`ui/panels/medicine.py`)
4. **Sidebar ntfy hint** — family-contact expander now shows the copyable subscribe URL with a one-line hint (en/si/ta). (`ui/panels/sidebar.py`)
5. **Prescription steps** — visible *Step 1 → Step 2 (confirm gate) → Step 3* markers (en/si/ta). (`ui/panels/prescription.py`)
6. **README drift** — `Conversation` not `ChatSession`, single `models.py` not a package, heuristic-first router not "CrewAI orchestrator", removed `OWNERS.md`/`BOOKING_AGENT_DESIGN.md` refs, `gemini-2.5-flash` in `project/README.md`, tests listing now says 52.
7. **New i18n keys** (all trilingual): `sidebar.family_ntfy_hint`, `panel.medicine.col_basket`, `panel.rx.step1`, `panel.rx.step2`.

## 👉 YOUR manual checks (browser — app is running at http://localhost:8501)

1. **Paste your Gemini key** into `project/.env` (`GEMINI_API_KEY=...`, no quotes), then restart the app. Without it everything runs in offline-fallback mode.
2. Login `demo1 / demo1pass` → sidebar: pick a city (e.g. Colombo).
3. Walk the 8-step demo script (plan Section D). Specifically eyeball:
   - Booking: book an alternative slot → **green success card must now appear** and stay until you dismiss it.
   - Medicine: "I need prices for Panadol and Amoxicillin" → complete pharmacies on top, "Has all?" column reads ✅/⚠️.
   - Prescription expander: Step 1 / Step 2 labels render; confirm gate works; Step 3 table appears above.
   - Sidebar → family contact: ntfy URL shows and is copyable; open it on your phone and re-test a push.
   - Logout → login: past chat threads reappear in the sidebar.
4. **With the key in**: one chat turn ("book me with Dr. Sunil Perera tomorrow at 10:00") → confirm it feels fast and check the terminal log for the Pydantic-AI marker; try voice input and prescription OCR on the sample image once (mind free-tier quota — don't burn it on repeats today).
5. Login demo3 (si) / demo4 (ta) for 2 minutes each — check nothing renders as a raw key like `panel.rx.step1`.

## 🏪 Phase 3 — Supplier portal (built & verified)

- Runs at **http://localhost:8502** (`streamlit run project/ui/supplier_portal.py --server.port 8502`).
- Verified at SQL level: Losartan flip at Union Chemists → patient view shows it (LKR 18) → seed state restored (still out-of-stock, so the live demo moment is intact). Slot publish + duplicate detection also verified.
- **Demo script for step 5:** portal tab → Pharmacy dashboard → Union Chemists → tick "In stock" on Losartan 50mg → 📣 Publish changes → switch to patient app → type "price of Losartan" → Union Chemists appears. Say: *"Suppliers publish INTO the platform — the platform is the source of truth, no third-party API dependency."*
- **After each rehearsal of that moment**, untick it and publish again (or just do the Saturday fresh-boot re-seed, which resets everything).
- Optional: set `SUPPLIER_PASSCODE=...` in `.env` to show a gate; left off by default.

## ⚠️ Notes / risks

- **Gemini free-tier quota**: `.env.example` warns about a daily cap. Rehearse mostly on the offline fallbacks; spend LLM calls only where the demo needs them (booking turn, panel review, one OCR).
- `ruff` isn't installed locally (`pip install -r requirements-dev.txt` if you want lint before committing) — pytest is green, which is the real gate.
- SonarLint complexity warnings on panel `render()` functions are pre-existing and not part of the project's ruff config — ignore for the viva.
