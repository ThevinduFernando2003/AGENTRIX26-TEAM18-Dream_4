# MedBridge AI — Build-Out Plan (PLAN1)

> Full, detailed plan to take the repo from "Tier 1–3 working prototype" to a
> **100%, properly-engineered source repo**: real RAG, real Pydantic AI,
> bug-fixed, tested, dockerised, CI'd, documented.
>
> Work is split across **4 members with non-overlapping file ownership**, in
> **4 sequential phases**. Each phase ends with a **full-team integration test**
> before the next phase starts.

---

## 0. Team & Ownership Map

To avoid two people editing the same file, every member **owns a fixed set of
modules for the whole project**. You only edit files in your lane. Shared
"god files" are split in Phase 1 so nobody collides afterwards.

| Member | Domain / Lane | Owns these paths (after Phase 1 refactor) |
|---|---|---|
| **Janidu** (lead) | RAG + Chatbot core + Integration + Architecture | `project/rag/**`, `project/agents/basic_chatbot.py`, `project/agents/emergency.py`, `project/ui/app.py` (thin shell), `project/ui/panels/chat.py`, `project/kb/rag_knowledge/**`, top-level `README.md` |
| **Thevindu** | Booking + Reminders + Pydantic AI | `project/agents/booking_agent.py`, `project/agents/reminders.py`, `project/ui/panels/booking.py`, `project/models/booking.py` |
| **Nisal** | Medicine + Vision/OCR + i18n + Voice | `project/agents/medicine_tracker.py`, `project/agents/vision_ocr.py`, `project/i18n/**`, `project/ui/panels/medicine.py`, `project/ui/panels/prescription.py`, `project/models/medicine.py` |
| **Chanupa** | Platform / Data / Auth / DevOps | `project/db/**`, `project/agents/specialist_panel.py`, `project/agents/moderator.py`, `project/notifications/**`, `project/ui/auth.py`, `project/ui/panels/emergency.py`, `project/ui/panels/report.py`, `project/models/__init__.py` + shared models, `Dockerfile`, `.github/**`, `pyproject.toml`, `requirements.txt`, `tests/conftest.py` |

### Shared-file rules (the only files more than one person needs)
- **`requirements.txt` / `pyproject.toml`** → owned by **Chanupa**. Others request a dependency by pinging him; he adds it. Never edit directly.
- **`project/models/`** → split into per-domain files in Phase 1 (see below). After the split each member edits only their own model file.
- **`project/ui/app.py`** → after Phase 1 it is a thin router that just calls panel modules. Only **Janidu** edits it.
- **`.env` / `.env.example`** → `.env` is gitignored. Edits to `.env.example` go through **Chanupa**.

### Branch & PR workflow
- One branch per member per phase: `p<phase>/<member>` (e.g. `p2/thevindu`).
- Branch off `Test`, PR back into `Test`. No direct commits to `Test`/`main`.
- A phase is **not done** until all 4 PRs are merged **and** the phase integration test passes.
- Commit messages: conventional + meaningful (the hackathon rubric checks git history).

---

## Phase 1 — Foundations, Critical Fixes & Parallel-Safe Refactor

**Goal:** make the repo safe to work on in parallel (split god-files), kill the
critical bugs, and lay the scaffolding the later phases depend on.

### Janidu
1. **Rotate the leaked `GEMINI_API_KEY`** in Google AI Studio (it is in git history). Put the new key only in local `.env` (now gitignored). Confirm `.env.example` has a placeholder.
2. **Refactor `ui/app.py`** into a thin orchestrator + a `project/ui/panels/` package — one module per panel (`chat.py`, `emergency.py`, `booking.py`, `medicine.py`, `prescription.py`, `report.py`, `sidebar.py`). `app.py` just imports and calls them. Define a simple, documented contract each panel follows (`render(user) -> None`, reads/writes `st.session_state`). This is what unblocks non-overlapping work for everyone.
3. Create **`project/rag/` package skeleton** with the interface the others will call in Phase 2: `retriever.py` exposing `retrieve(query: str, collection: str, k: int) -> list[dict]` (stubbed to return `[]` for now), plus a docstring describing the contract.
4. Fix **`current_user()` cache staleness** ([auth.py](project/ui/auth.py)) — coordinate with Chanupa since he owns `auth.py`; you specify the desired behaviour, he merges. (Or: move the cache logic into a helper you both agree on.)
5. Own `chat.py` panel + `basic_chatbot.py` + `emergency.py`.

### Thevindu
1. Take ownership of **`ui/panels/booking.py`** (the booking panel lifted out of `app.py` by Janidu's refactor).
2. Fix the **reminder-vs-booking intent collision**: today `detect_reminder()` in `basic_chatbot.py` fires before routing, so "book a follow-up in 2 weeks" never reaches booking. Agree a rule with Janidu (e.g. only treat as reminder when no booking verb present) and implement on the booking side / routing hand-off.
3. Move booking schemas into **`project/models/booking.py`** (after Chanupa splits `models.py`).
4. Write down (no code yet) the **Pydantic AI booking agent design** you'll build in Phase 2 — tools, typed inputs/outputs — as a short comment block or `docs/booking_agent.md`.

### Nisal
1. Take ownership of **`ui/panels/medicine.py`** and **`ui/panels/prescription.py`**.
2. Fix **partial i18n**: booking/medicine/report **panel** text currently stays English for si/ta users. Introduce a consistent approach — either add catalog keys in `i18n/translate.py` for panel strings, or wrap agent/panel messages through `translate_dynamic`. Document the pattern so other panels follow it.
3. Move medicine schemas into **`project/models/medicine.py`**.
4. Audit `i18n/translate.py` CATALOG for missing keys after the panel split.

### Chanupa
1. **Split `models.py`** into a `project/models/` package: `__init__.py` (re-exports for back-compat), `common.py` (shared `Literal`s, base), `chat.py`, `booking.py`, `medicine.py`, `panel.py`. Keep `from project.models import X` working so nothing breaks. **Do this first** — it unblocks Thevindu/Nisal/Janidu.
2. **Fix the logout cross-user state leak** ([auth.py:99](project/ui/auth.py#L99)): `logout()` only clears 4 keys; `last_panel`, `pending_*`, `tts_on`, etc. survive into the next login → one user sees another's panels. Clear all app session keys on logout (or namespace session state per `user_id`).
3. **Schema hardening** ([db/schema.sql](project/db/schema.sql)): add `UNIQUE(doctor_id, date, time)` to `AppointmentSlot`; remove or wire the dead `APP_SECRET`.
4. **Pin dependencies**: pin `crewai` to a tested version (installed is `1.9.3`, requirements say `>=0.41` — confirm which API you target), keep `bcrypt>=4.0`. Add `chromadb` explicitly (currently only transitively present).
5. Create **`pyproject.toml`** with `ruff` + `black` config and project metadata (resolves the `sys.path` hack long-term).
6. Own `auth.py`, `ui/panels/emergency.py`, `ui/panels/report.py`, `db/**`, `specialist_panel.py`, `moderator.py`, `notifications/**`.

### ✅ Checkpoint 1 (whole team)
- App launches; **every panel renders** from the new `ui/panels/` structure.
- Login → logout → login as a different user shows **no leaked state**.
- `models.py` split done, all imports work, app runs.
- Smoke-test each flow (chat, emergency, booking, medicine, report, prescription, reminders) once.

---

## Phase 2 — Headline Features: real RAG + real Pydantic AI

**Goal:** make the code actually match the Interim Report — implement RAG
(Chroma) grounding and a genuine Pydantic AI agent. **Priority: RAG first**
(biggest code-review/defense risk), Pydantic AI second.

> **Free-tier rule:** use **Gemini `text-embedding-004`** (free tier) for
> embeddings, persisted in **Chroma** (already installed via CrewAI). Provide a
> deterministic offline fallback (no key → keyword/`difflib` path) so the demo
> still runs, exactly like the existing agents.

### Janidu — RAG subsystem (priority)
1. Build `project/rag/` fully:
   - `ingest.py` — reads `project/kb/**` + a new curated `project/kb/rag_knowledge/` (symptom→specialty notes, facility descriptions, medicine notes), chunks, embeds (Gemini free tier), writes to a **persistent Chroma** dir (gitignored; Chanupa adds the path to `.gitignore`).
   - `retriever.py` — implement `retrieve(query, collection, k)` for real (was stubbed in Phase 1).
   - Idempotent re-ingest; offline fallback returns `[]` cleanly.
2. **Wire the chatbot to RAG**: `basic_chatbot.py` grounds specialty suggestions using `retrieve(...)` instead of guessing — and never invents facilities/specialties not in the index.
3. Document the RAG flow for the technical defense (`docs/rag.md`).

### Thevindu — Pydantic AI Booking agent (priority 2)
1. Implement a **real `pydantic_ai.Agent`** for booking with typed tools (`find_doctors`, `find_slot`, `nearest_alternatives`, `book`) and a validated `BookingResponse` output. Keep the existing deterministic `process()` as the offline fallback path.
2. Use Janidu's `retrieve(...)` to resolve fuzzy specialty/doctor queries to real DB rows before booking.
3. Make `book()` still atomic; the agent must not double-book.

### Nisal — Medicine grounding + flows
1. Upgrade medicine resolution to use **RAG/vector match** over the medicine catalog (replacing/augmenting `difflib`) via Janidu's retriever.
2. Harden the OCR-confirm gate and voice (STT/TTS) flows; ensure dosage is still verbatim-only.
3. (If time, lower priority) a second Pydantic AI agent for the medicine tracker — otherwise keep structured.

### Chanupa — Platform support for the new features + test harness
1. Stand up the **pytest harness** others will use in Phase 3: `tests/conftest.py` with a **temp seeded SQLite** fixture, a fixture to point the app at a throwaway Chroma dir, and env stubs for "no API key" mode.
2. Manage new deps/config (Chroma persist dir, embedding model id) via settings + `.gitignore`.
3. Keep `specialist_panel.py` / `moderator.py` compatible with any model-id config changes.

### ✅ Checkpoint 2 (whole team)
- With a real key: chatbot specialty suggestions are **RAG-grounded**; booking goes through the **Pydantic AI agent**.
- Without a key: everything still runs on deterministic fallbacks.
- Re-running ingestion is idempotent; no duplicate vectors.

---

## Phase 3 — Make Every Flow Work, Fast, with Finished UI

**Goal:** turn "the code runs" into "the demo works and feels instant." Phase 2
made RAG + routing real; Phase 3 fixes the two functional defects found in P2
verification, removes the perceived **"stuck"**, and finishes the UI/UX of every
flow in the Interim Report. **No new domains** — make the promised ones demo-grade.
Each member also writes tests **for their own lane** (non-overlapping).

> **Carry-over from Phase 2 verification — read before starting:**
> - 🔴 **Perceived "stuck" on booking/medicine is LLM latency, NOT a missing search API.** Search runs on the seeded SQLite and works: booking returns 5 alternative slots, medicine returns 5 pharmacies with price/stock/distance. The chat router goes through CrewAI `crew.kickoff()` (~5 s every message), and on a throttled key litellm retries 429s with backoff → 30–60 s hangs. Fixing routing latency fixes the "stuck."
> - 🔴 **The Pydantic AI booking agent is dead.** `_get_booking_agent()` raises `name 'RunContext' is not defined` (imported *inside* the function but resolved against module globals under `from __future__ import annotations`), so `process_agentic()` silently falls back to deterministic. The headline "real Pydantic AI" is never actually exercised.
> - ✅ **Seed/mock data is by design** (offline-capable) and is a demo *strength*. Do **NOT** add external/live pharmacy or doctor APIs — there is nothing to integrate.

### Janidu — routing speed + chat UX + history view
1. **Kill the latency (the #1 demo blocker).** In `basic_chatbot`, route **heuristic-first** for unambiguous intents (booking/medicine/report verbs) and only call the LLM when the heuristic is uncertain (`route == "general"`). Replace the heavy CrewAI router in `_run_llm` with a single **direct Gemini JSON call** (CrewAI's Agent/Task/Crew overhead is most of the 5 s). Set a hard **request timeout (~8 s) and `num_retries=0`** so a rate-limited key fails fast to the heuristic instead of hanging.
2. **Chat never looks frozen.** Wrap `basic_chatbot.handle(...)` in `st.spinner(...)`; echo the user's message immediately; disable the input while a turn is in flight.
3. **Persistent history view (Interim §3.5).** Add a "History / Timeline" panel that reads the user's past chats, appointments, report reviews and medicine searches from the DB into one chronological view (hand new strings to Nisal for si/ta).
4. Tests: heuristic-first router classification; RAG retrieval correctness + ingest idempotency; `emergency.screen` true/false positives.

### Thevindu — make the Pydantic AI booking agent real + reminders demo
1. **Fix `_get_booking_agent`**: move `from pydantic_ai import Agent, RunContext` + the Gemini provider imports to **module level** (guarded `try/except` → `None` for the offline path) so tool annotations resolve. Confirm `process_agentic` actually runs the agent (not the fallback) when a key is present; add `request_timeout` + bounded retries so the AFC tool loop can't hang.
2. **Prove the agent earns its place**: "book me a heart doctor next Tuesday" should resolve specialty via RAG → real doctor → real slots end-to-end *through the agent*.
3. **Future-visit reminder demo (Interim §3.3)**: verify `detect_reminder` → `_persist_reminder` → sidebar "Check my reminders" → `reminders.fire` → ntfy push, end-to-end. Seed one near-due reminder so the demo shows a push in one click.
4. Booking panel UX: `st.spinner` around `process_agentic`/`book`; clear "tell me a doctor or specialty" message when nothing was extracted.
5. Tests: `parse_date`/`parse_time`, `nearest_alternatives` ordering, atomic `book()` (no double-book under retry), **agent path is taken when keyed** + typed-output validation, `detect_reminder` regex.

### Nisal — voice, OCR, i18n completion
1. **Verify + harden STT (voice in) and gTTS (voice out)** (Interim §3.5) on real audio: graceful "unavailable" with no key; Sinhala/Tamil/English all round-trip; spinner during transcription.
2. **Prescription OCR demo path**: Gemini Vision → confirm-gate → pharmacy search; ship a sample prescription image (or keep the paste fallback) so the flow demos even without a photo. Dosage stays **verbatim** — never AI-generated.
3. Localize every new string Janidu/Thevindu add (history view, chat spinner, booking needs-info); re-run the catalog-completeness check (every key has en/si/ta).
4. Tests: `match_medicines`, `haversine_km`, `quotes_for` (totals/missing), **OCR-confirm gate fires no pharmacy lookup before confirm**, i18n completeness, `translate_dynamic` offline fallback.

### Chanupa — data/agents support + test harness
1. **Specialist panel with a paid key**: confirm the 3 specialists return real, *distinct* analyses (not the stub fallback) and the moderator surfaces real agree/disagree; ensure errors fall back to stub cleanly and log why.
2. **Demo seed review**: every specialty has ≥1 doctor with available slots in the next 7 days (booking always shows alternatives), and pharmacies stock the demo medicines.
3. Keep `tests/conftest.py` fixtures green; add auth (hash/verify, dup-username), seed idempotency, notifications-log-on-failure tests. Wire all lanes into one `pytest` run.
4. Tighten the greedy `\{.*\}` JSON regex across chatbot/moderator/specialist to non-greedy/balanced extraction.

### ✅ Checkpoint 3 (whole team)
- "Book a doctor" / "price of paracetamol" return results in **< 3 s** with no perceived hang — online and offline.
- Booking demonstrably runs through the **Pydantic AI agent** with a key (confirmed in logs/test); deterministic fallback without.
- Every Interim-Report flow works in the browser in **en/si/ta**: chat, emergency, booking, future-visit reminder push, medicine comparison, prescription OCR+confirm, specialist panel, history view.
- `pytest` green.

---

## Phase 4 — Package, Prove, and Deliver (DevOps + Docs + Demo)

**Goal:** make it runnable by a judge in one command, prove it end-to-end, and
produce every required deliverable. **No feature work** — only packaging,
documentation, and demo prep.

### Whole team
- **Joint end-to-end dry run** against a real key: the full Interim-Report walkthrough, every flow, every language, online **and** offline (key unset). Log any regression as a P4 blocker.

### Chanupa — DevOps / packaging (the bulk)
1. **`Dockerfile`** (slim Python 3.12, install `requirements.txt`, run Streamlit) + **`.dockerignore`** + **`docker-compose.yml`** with volumes for `project/db/app.db`, `project/rag/chroma_store`, and `.env` passthrough. The app already auto-seeds the DB and auto-ingests RAG on first boot, so `docker compose up` is cold-start-to-working with no manual steps.
2. **`.github/workflows/ci.yml`**: `ruff` + `black --check` + `pytest` on push/PR (offline mode, no key); optional Docker build.
3. Pin/verify deps: `pydantic-ai`, `google-generativeai`/`google-genai`, `chromadb`, `onnxruntime`, `gTTS`, `streamlit-geolocation`. Repo-wide lint/format clean; optional `pre-commit`.
4. **Secrets audit**: confirm the leaked key is rotated; document the git-history exposure and that `.env` is gitignored; `CONTRIBUTING.md` + release checklist; tag a release.

### Janidu — docs + architecture
1. Rewrite **`README.md`** to match reality: RAG = local Chroma/ONNX by default (optional Gemini embeddings via `RAG_EMBED_BACKEND`); routing = heuristic-first + direct Gemini JSON; Pydantic AI booking; CrewAI specialist panel. Remove prior overclaims; include exact run steps (local **and** Docker) and the offline story.
2. **Architecture diagram** (Streamlit → panels → agents → RAG/DB/ntfy/Gemini) — required deliverable.
3. Own the **E2E test script / demo checklist**.

### Thevindu / Nisal — required diagrams + video
- **Thevindu**: **ER diagram** from `db/schema.sql` — required deliverable.
- **Nisal**: **Use-case diagram** — required deliverable; record the **1–2 min demo video (no voiceover)** per hackathon rules.

### Demo assets (whole team, lead: Janidu)
- **`DEMO.md`** — a scripted walkthrough on the seeded `demo*` accounts: which user to log in as, the exact phrase to type for each flow, and the expected on-screen result — including a Sinhala/Tamil pass and an offline (no-key) pass. This is what guarantees a smooth live demo.

### ✅ Final Checkpoint
- `docker compose up` serves a fully working demo at `localhost:8501` (cold start, no manual ingest).
- Full system test passes online **and** offline; all flows in en/si/ta.
- README accurate; ER + architecture + use-case diagrams committed; demo video recorded; `DEMO.md` script verified.
- CI green, lint clean, key rotated. **Repo + demo at 100%.**

---

## Appendix A — Critical bug/issue tracker (fold into the phases above)

| # | Severity | Issue | Where | Owner | Phase |
|---|---|---|---|---|---|
| 1 | 🔴 | Live `GEMINI_API_KEY` in git history | `project/.env` | Janidu | 1 |
| 2 | 🔴 | Logout leaks state across users | [auth.py:99](project/ui/auth.py#L99) | Chanupa | 1 |
| 3 | 🔴 | Report claims RAG — none in code | (new `rag/`) | Janidu | 2 |
| 4 | 🟠 | Report claims Pydantic AI — none in code | `booking_agent.py` | Thevindu | 2 |
| 5 | 🟠 | `crewai` version drift (`>=0.41` vs `1.9.3`) | `requirements.txt` | Chanupa | 1 |
| 6 | 🟠 | Partial i18n (panel text English for si/ta) | `ui/panels/*`, `i18n/` | Nisal | 1 |
| 7 | 🟡 | Greedy `\{.*\}` JSON regex | chatbot/panel/moderator | owner-per-file | 2/3 |
| 8 | 🟡 | `current_user()` cache staleness | `auth.py` | Janidu+Chanupa | 1 |
| 9 | 🟡 | Reminder vs booking intent collision | `basic_chatbot.py` | Thevindu | 1 |
| 10 | 🟡 | No `UNIQUE` on `AppointmentSlot(doctor,date,time)` | `schema.sql` | Chanupa | 1 |
| 11 | 🟢 | Dead `APP_SECRET` config | `.env` | Chanupa | 1 |

## Appendix B — Household / refactoring checklist (the "chores")

- [ ] Split `models.py` → `models/` package (Chanupa, P1)
- [ ] Split `ui/app.py` → `ui/panels/` package (Janidu, P1)
- [ ] `pyproject.toml` + ruff/black config (Chanupa, P1)
- [ ] Pin all deps; add `chromadb` explicitly (Chanupa, P1)
- [ ] `tests/` + `conftest.py` harness (Chanupa, P2) → per-domain tests (all, P3)
- [ ] `Dockerfile` + `.dockerignore` + `docker-compose.yml` (Chanupa, P3)
- [ ] `.github/workflows/ci.yml` (Chanupa, P3)
- [ ] `pre-commit` config (Chanupa, P3, optional)
- [ ] `.gitignore` for Chroma persist dir (Chanupa, P2)
- [ ] README accuracy rewrite (Janidu, P4)
- [ ] ER / architecture / use-case diagrams (Thevindu / Janidu / Nisal, P4)
- [ ] Demo video, no voiceover (Nisal, P4)
- [ ] `CONTRIBUTING.md` + release checklist (Chanupa, P4)

## Appendix C — Dependency notes
- **Embeddings:** Gemini `text-embedding-004` (free tier) — keeps the "free tier only" rule.
- **Vector store:** **Chroma** (already installed via CrewAI; persistent local dir). Standardise on Chroma; FAISS optional.
- **Pydantic AI:** `pydantic-ai` 0.4.3 installed.
- All new AI must keep an **offline deterministic fallback** like the existing agents.
