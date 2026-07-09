# MedBridge AI — 2-Day Viva Wrap-Up Plan (Janidu + Nisal)

**Viva:** Saturday 11 July 2026, morning (online code review, industry professionals)
**Executors:** Janidu (J) and Nisal (N) only. ~12–16 h each available.
**Demo mode:** Gemini API key + internet available → **online path is primary**, offline fallback is the safety net.
**Repos:** Evaluators inspect the **frozen** `AGENTRIX26-TEAM18-Dream_4` repo. We demo live from **this** repo (`MedBridge-AI`), which is the rule-#4-compliant "continue in a brand-new repository" copy. **Never push anything to the frozen repo.**

---

## 0. Strategy — where the hours actually pay off

Because the evaluators read the *frozen* code, code changes here are only visible through the live demo.
So the budget is deliberately weighted:

| Bucket | Share | Why |
|---|---|---|
| A. Demo-visible UI/UX polish + bug sweep | ~45% | What they *watch* for 15 minutes shapes the whole impression |
| B. Defense mastery (architecture, NFRs, API story, drift answers) | ~35% | They ask directly on architecture, diagrams, NFRs — this is where teams get disqualified ("can't prove it's your code") |
| C. Rehearsal + contingency | ~20% | Two full dry runs; nothing improvised on Saturday |

**The one-liner if asked why the demo differs slightly from the frozen repo:**
> "The frozen repo is our untouched 12-hour state. Per rule 4 we continued polishing in a separate repository — everything architectural is identical; the changes are visual polish and copy."

**Current verified baseline (Thu):** all 52 offline tests pass; structure matches the viva guide; no `.env` on this machine yet (app runs in fallback mode until Phase 0 fixes that).

---

## 1. Ground rules (both of you)

1. Work on branch `viva-prep`. Small commits, conventional messages (`ui:`, `fix:`, `docs:`), **pull before every push**.
2. Run `python -m pytest tests/ -q` before every push. 52 must stay green.
3. **No feature additions, no schema changes, no agent redesign.** Polish, copy, layout, bug fixes only. Anything bigger creates a frozen-repo divergence you'll have to explain under pressure.
4. File ownership below is absolute — never edit the other person's files. That is the whole merge-conflict strategy.

### File ownership (zero overlap)

| Owner | Files |
|---|---|
| **Janidu** | `ui/app.py`, `ui/common.py`, `ui/auth.py`, `ui/panels/chat.py`, `sidebar.py`, `emergency.py`, `history.py`, `booking.py`*, `agents/basic_chatbot.py`, `agents/emergency.py`, `agents/booking_agent.py`*, `rag/*`, `Readme.md`, `docs/*`, this plan |
| **Nisal** | `ui/panels/medicine.py`, `prescription.py`, `report.py`, `agents/medicine_tracker.py`, `vision_ocr.py`, `specialist_panel.py`*, `moderator.py`*, `i18n/*` (incl. the full `translate.py` catalog), `kb/*` seed + sample files |

\* Thevindu's/Chanupa's verticals split between you for *polish only* (scope agreed: full repo fair game). Booking sits with J because it's routed from chat; report/panel sits with N because it shares the upload/confirm UX patterns with prescription.

**i18n rule:** every new/changed UI string goes through `t()` keys. J lists needed keys in a `# TODO(i18n)` comment in his file; N adds them to the catalog (his file). Never both editing `translate.py`.

---

## 2. Phase 0 — Baseline & triage (Thursday evening, ~2–3 h, together)

- [ ] Create `project/.env` from `.env.example`; set `GEMINI_API_KEY`, confirm `GEMINI_MODEL=gemini-2.5-flash`. Verify with one chat turn that the LLM path answers (check logs for the Pydantic-AI marker on a booking).
- [ ] Fresh run: delete `project/db/app.db` + `chroma_store/`, `streamlit run project/ui/app.py`, log in `demo1/demo1pass`. Confirm auto-seed + auto-ingest work from clean state (this is exactly what a demo restart looks like).
- [ ] Walk the 8-step demo script (Section 6) once, badly. Note every visual wart, confusing label, dead end, or slow moment in a shared `TRIAGE.md` scratch list (don't fix anything tonight).
- [ ] Verify the four demo linchpins: emergency regex fires; Dr. Sunil Perera tomorrow-10:00 conflict produces alternatives; medicine table sorts by cost+distance after setting city; demo1's near-due reminder fires a push.
- [ ] Both: subscribe a phone to the ntfy topic and confirm a real push arrives.
- [ ] Split `TRIAGE.md` items by file ownership; anything ambiguous goes to whoever owns the panel.

**Exit:** app runs clean from scratch with the key; triage list exists and is divided.

---

## 3. Phase 1 — Parallel polish (Friday ~09:00–15:00)

### Janidu (~5 h)

1. **Chat panel first impression** — welcome/empty state that advertises capabilities ("Try: *I have chest pain* · *Book Dr. Silva tomorrow 10am* · *Price of Panadol*"). Clear spinner text ("Checking symptoms…" not a bare spinner).
2. **Thread persistence made obvious** (your own doubt): sidebar thread list must visibly show past conversations after logout→login. Add relative timestamps / first-message titles if missing.
3. **Sidebar grouping**: Profile / Language / Location / Family contact / Reminders / Logout as labeled sections. Add a copyable ntfy topic + one-line "family subscribes at ntfy.sh/<topic>" hint — this makes the emergency demo self-explanatory.
4. **Emergency + booking panels**: confirm-flow copy is calm and clear; booked-slot success state is unmistakable (fee, doctor, date, push-sent note).
5. **Readme.md accuracy sweep** (this repo only): fix the known drift — `models.py` is one file not a package, table is `Conversation` not `ChatSession`, default model `gemini-2.5-flash`, remove references to files that don't exist (`OWNERS.md`, `docs/BOOKING_AGENT_DESIGN.md`). A clean README in the demo repo buys credibility even if they never read it.
6. **Redraw the architecture diagram.** The report's Figure 8.1 is unreadable — and evaluators reportedly ask *directly* on the architecture diagram. Produce one clean Mermaid/draw.io diagram of the six layers + request flow (§1.5–1.6 of the viva guide is the source of truth). Export to `docs/architecture.png` and have it open in a tab during the viva.

### Nisal (~5 h)

1. **Medicine comparison table**: LKR formatting, distance in km with 1 decimal, out-of-stock rendered as a visible badge/strikethrough not just a list, cheapest row highlighted. Column order: Pharmacy → Total → Distance → Items → Missing.
2. **Prescription flow as numbered steps**: "1 Upload/paste → 2 Confirm text → 3 Compare pharmacies". Make the confirm gate visually unmistakable (it's your flagship safety feature — the UI should look like a gate).
3. **Report/specialist panel**: three columns readable at demo zoom; confidence bars labeled; disagreements as warnings that *pop*. Moderator consensus visually distinct from the three opinions.
4. **i18n spot-check**: log in as demo3 (si) and demo4 (ta); walk all panels; fix broken/missing keys, ensure fonts render, confirm English passthrough messaging when translation is skipped.
5. **Seed/demo-data hygiene**: doctor names, facility names, prices look plausible; sample reports and the sample prescription image produce good panel/OCR output with the key present (rehearse the *online* OCR now that we have a key).
6. Add any `TODO(i18n)` keys J left.

**Checkpoint 15:00 Friday:** merge both work streams on `viva-prep`, pytest green, 15-minute joint click-through.

---

## 4. Phase 2 — Hardening + defense material (Friday ~15:00–19:00)

### Janidu (~3 h)

1. **Security quick win (stretch, only if smooth):** HMAC-sign the `?uid=` remember-me param with a secret from `.env` (~20 lines in `ui/auth.py` + a test). Whether or not you ship it, it becomes a first-class viva answer: *"unsigned in the 12-hour build — we knew, and signed it in the polish repo."*
2. Write `docs/DEFENSE.md` — the answer sheet (content in Sections 7–8 below): third-party API story, security/PDPA narrative, NFR list, drift honesty list. This is the file both of you memorize.
3. Prune anything embarrassing from the demo DB path (test users, junk conversations) — fresh seed only.

### Nisal (~3 h)

1. **Demo assets**: one clean handwritten-style prescription photo that OCRs well; verify all three sample reports give a good three-specialist + disagreement demo with the live key (run each once; note which report gives the most interesting disagreement — use that one on Saturday).
2. **Record a 2–3 min backup screen capture** of the full happy-path demo (silent). If Streamlit/key/network dies mid-viva, you narrate over the recording instead of debugging live.
3. Final i18n pass on any strings J's polish introduced.

**Checkpoint 19:00 Friday:** feature-freeze `viva-prep`. Nothing but typo fixes after this. pytest green, tag it mentally as the demo build.

---

## 5. Phase 3 — Learn + rehearse (Friday evening ~2 h + Saturday pre-viva ~1.5 h)

### Friday evening — full dress rehearsal #1 (together, ~2 h)
- Run the demo script end-to-end, timed (target ≤ 12 min including talking).
- Then interrogate each other from the Q&A bank (Section 9) — J asks N's sections, N asks J's. Anything answered weakly gets 20 minutes of guide re-reading (`MedBridge_Viva_Guide.md`: J owns Part 3-A + §1.5–1.7; N owns Part 3-C; **both** own Part 1, §1.11 drift list, and Part 4).
- Rehearse the two *absent-member* topics, since Thevindu/Chanupa's verticals may be asked to whoever is present: J covers **booking/atomicity/Pydantic-AI** (guide Part 3-B), N covers **specialist panel independence + moderator guard** (Part 3-D). You don't need their depth — you need the 60-second versions plus one code location each.

### Saturday morning (before viva, ~1.5 h)
- Fresh-boot the app once (clean DB, ingest, login) 45+ min before the slot; leave it running.
- Pre-open tabs: app · ntfy topic · architecture diagram · ER/use-case diagrams · `docs/DEFENSE.md` · backup recording.
- Dress rehearsal #2: demo script once, fast, no talking. Phone charged for the ntfy push moment.
- Read the drift list (§1.11 + Section 8 below) out loud one final time — the worst viva moment is an examiner finding a doc-vs-code mismatch you knew about but forgot.

---

## 6. Demo script (online-path primary, ~10–12 min)

> Login: `demo1 / demo1pass`. City set. ntfy tab + phone subscribed. Key loaded.

| # | Action | Say this |
|---|---|---|
| 1 | Intro (30 s) | "MedBridge AI is a healthcare *navigator*, never a diagnoser — five agent groups behind one trilingual chat. Everything runs on free tier, and every AI feature has a deterministic fallback." |
| 2 | `I have severe chest pain and can't breathe` | "Emergency screening is pure regex and runs *before* any LLM — zero latency on the safety path." Confirm → tel:1990 + show phone receiving the family push. |
| 3 | `Book me with Dr. Sunil Perera tomorrow at 10:00` | "That slot is taken — the Pydantic AI agent proposes nearest alternatives via typed SQL tools; only deterministic code ever writes the booking, atomically." Book one → push arrives. |
| 4 | `I need prices for Panadol and Amoxicillin` | "RAG-grounded name matching with an edit-distance precision guard; sorted by total cost then distance." |
| 5 | Upload sample report → run panel | "Three CrewAI specialists run in separate threads with no shared state — independence is structural. The moderator is *forbidden by code* from returning an empty disagreement list." |
| 6 | Prescription photo → OCR → confirm gate | "Gemini Vision transcribes; nothing happens until the human confirms — dosage text is only ever shown verbatim from the catalog." |
| 7 | Switch to demo3 (Sinhala) — one chat turn | "Full trilingual UI, static catalog + cached dynamic translation, plus voice in/out." |
| 8 | `Doctor asked me to come back in 2 weeks` → sidebar reminder → push | "Reminder detection is regex, idempotent, and yields to booking intent when both fire." |
| Close | — | "Turn the API key off and this entire demo still runs on deterministic fallbacks. Structural safety, graceful degradation — that's the architecture." |

**Contingencies:** Gemini 429 mid-demo → fallbacks kick in automatically; *narrate it as the designed behavior, not an apology*. Streamlit crash → backup recording. ntfy silent → show `NotificationLog` rows ("every attempt is audited").

---

## 7. Defense: the third-party API question (memorize)

**Q: "Why is pharmacy/doctor/slot data in your own schema? Shouldn't that come from third-party APIs?"**

Answer in three moves:

1. **Split the schema.** User-owned tables (`User`, `ChatMessage`, `Appointment`, `Prescription`, `FutureVisitReminder`, `MedicalReport`, `NotificationLog`) are our system of record *by design* — no third party stores a user's bookings, chats, or reminders for us. That half of the schema is production-correct, not a mock.
2. **Name the reality.** Sri Lanka has **no public pharmacy-stock API and no open channeling API** — eChannelling/Doc990 are closed, and that fragmentation is literally the problem statement of our domain. The rules also mandated free-tier only. So catalog tables (`Doctor`, `Facility`, `AppointmentSlot`, `Pharmacy`, `Medicine`, `PharmacyMedicinePrice`) hold curated seed data labeled `SEED DATA — not live` in every file, in logs, and in the UI banner.
3. **Show the seam.** Agents never query those tables directly — they call typed tools (`find_doctors()`, `nearest_alternatives()`, `quotes_for()`, `retrieve()`). A real integration replaces the tool body with an API adapter; no agent, panel, or model changes. And in production you'd *keep* these tables as a cache layer anyway (rate limits, latency, offline resilience).

> One-liner: *"The DB is our integration boundary — user data is ours by design; catalog data is a labeled mock behind tool interfaces that a real API drops into without touching any agent."*

---

## 8. Defense: security, privacy & compliance (memorize)

**What we actively do (lead with these):**
- bcrypt for every password including seed users; no plaintext anywhere.
- Full session wipe on logout (fixed cross-user leak in Phase 1) — session isolation.
- Disclaimers injected by **UI code**, not prompts — a malformed generation cannot drop them. Symptom → *specialty* only, never a disease.
- OCR confirm gate: no pharmacy action on unconfirmed machine-read text. Dosage shown verbatim from catalog only.
- Every notification attempt audited in `NotificationLog`.
- `.env` gitignored; leaked key was rotated during the event; Cloud secrets via `st.secrets`.
- Per-user data scoping: every query filters on `user_id`; cascade deletes on user-owned data.

**Limitations we volunteer before they find them:**
- `?uid=` remember-me is **unsigned** → demo-grade only; production = signed session cookies/JWT. *(If the HMAC stretch shipped: "we've since signed it in the polish repo.")*
- ntfy topics are guessable → production = authenticated push (FCM/APNs) or ntfy access tokens.
- SQLite unencrypted at rest, single file → production = Postgres, encryption at rest, TLS everywhere, role-based access.
- No rate limiting / brute-force lockout on login.

**Compliance frame (strong local card):** a production version handles health data, a *special category* under **Sri Lanka's Personal Data Protection Act No. 9 of 2022** — requiring consent, purpose limitation, breach notification, and security safeguards; internationally, the same posture as GDPR Art. 9 / HIPAA-style controls. "The prototype's structural safety choices (UI-enforced disclaimers, confirmation gates, audit logs) are the seeds of that compliance posture."

**Doc-vs-code drift — own it (evaluators read the frozen repo):**
- Report claims Docker/CI/DEMO.md were delivered; they're not in the repo → "the report section was written from our plan; those items didn't land in the 12-hour window — the deterministic fallbacks and tests did."
- README shows `models/` package; reality is single `models.py`. `ChatSession` → actual table `Conversation`. README says `gemini-1.5-flash`; code default is `gemini-2.5-flash`. Chatbot docstring says CrewAI routing; it was replaced with a direct timed Gemini JSON call (and *why*: CrewAI added ~5 s and retried 429s into 30–60 s hangs). CrewAI is genuinely used for the specialist panel.

---

## 9. Q&A drill bank (rehearse Friday night)

Beyond the per-member questions in `MedBridge_Viva_Guide.md` Part 3 and the gotchas in Part 4, drill these evaluator-flavored ones:

1. Walk me through your architecture diagram. *(J leads — six layers, then the chat-turn lifecycle §1.6.)*
2. Where exactly does the LLM sit, and what happens when it's down? *(Both — the LLM/no-LLM table, guide Part 4.)*
3. Why Streamlit and not a "real" frontend? *(12-hour constraint; pure-Python velocity; the panel-contract architecture means a React front-end would swap the presentation layer without touching agents.)*
4. Your data is fake — what's real here? *(The orchestration, agents, RAG, atomic booking, safety gates are real; catalog data is labeled seed behind swappable tools — Section 7.)*
5. How do you protect a user's medical reports? *(Section 8, lead with per-user scoping + bcrypt + session isolation, volunteer the limitations.)*
6. Prove you wrote this. *(Each of you names your files, walks one function line-by-line: J → `ground_specialty()` + heuristic router; N → `_rag_resolve_medicine()` guard + confirm gate. Know your git history: `git log --author`.)*
7. What breaks at 10,000 users? *(SQLite writer lock → Postgres; Streamlit session model → stateless API + queue; ntfy → FCM; Gemini free tier → paid tier or self-hosted models.)*
8. Non-functional requirements — name yours. *(Security, privacy/compliance, reliability = graceful degradation, performance = heuristic-first <3 s, usability = trilingual + voice, maintainability = 52 offline tests + lint + panel contract, cost = free-tier only.)*
9. What would you do with two more weeks? *(Real integrations behind the existing tool seams, signed sessions, Postgres, retrieval-quality evaluation, pilot with one pharmacy chain.)*
10. Why is the demo app slightly different from the frozen repo? *(The rule-#4 one-liner, Section 0.)*

---

## 10. Timeline at a glance

| When | Janidu | Nisal |
|---|---|---|
| **Thu eve (2–3 h)** | Phase 0 together: env+key, fresh-boot, demo walk, triage split | same |
| **Fri 09–15** | Chat/sidebar/emergency/booking polish · README fix · architecture diagram | Medicine/prescription/report polish · i18n sweep · seed hygiene |
| **Fri 15:00** | ✅ Merge + pytest + joint click-through | ✅ |
| **Fri 15–19** | HMAC stretch · `docs/DEFENSE.md` · demo-data prune | Demo assets · backup recording · final i18n |
| **Fri 19:00** | 🔒 Feature freeze | 🔒 |
| **Fri eve (2 h)** | Dress rehearsal #1 + mutual Q&A drill + absent-member topics | same |
| **Sat pre-viva (1.5 h)** | Fresh boot, tabs open, rehearsal #2, drift read-aloud | same |

**Definition of done:** app boots clean from scratch with the key · demo ≤ 12 min rehearsed twice · both can answer every question in Sections 7–9 without notes · backup recording exists · pytest green on `viva-prep`.
