# MedBridge AI — Final Solo Viva Plan (Janidu, Friday → Saturday morning)

**Viva:** Saturday 11 July 2026, morning · online · **all four members attend** (each defends their own vertical).
**Demo:** local machine, Gemini key + internet → online path primary, offline fallbacks as safety net.
**Repos:** evaluators inspect the **frozen** `AGENTRIX26-TEAM18-Dream_4` repo; you demo from this polish repo (rule-#4 compliant). **Never push to the frozen repo.**

> If asked why the demo differs from the frozen repo:
> *"The frozen repo is our untouched 12-hour state. Per rule 4 we continued in a separate repository — the architecture is identical; the changes are polish, plus a supplier-portal concept demo that shows where the product goes next."*

---

## 0. Operating rules (read once, then execute)

1. **Priority order is absolute.** Every phase list is ordered; when a phase's timebox expires, cut from the bottom and move on. A finished demo beats any single unfinished improvement.
2. `python -m pytest tests/ -q` (52 green) before closing each phase that touched code.
3. **Main app gets polish only** — no features, no schema changes. The only new code is the supplier portal, and it lives in a **separate file on a separate port** so it cannot break the patient app.
4. Commit small and often on `viva-prep` (you commit; suggested messages inline).

### Suggested Friday clock (shift everything if you start later — keep the *order*)

| Block | Phase |
|---|---|
| 09:00–10:30 | Phase 0 — baseline & triage |
| 10:30–14:30 | Phase 1 — demo-critical polish |
| 14:30–16:30 | Phase 2 — defense pack + teammate sync |
| 16:30–19:30 | Phase 3 — supplier portal (**hard timebox**) |
| 20:00–22:00 | Phase 4 — record backup, rehearse, drill |
| Sat, viva −1 h | Phase 5 — final boot & run |

---

## Phase 0 — Baseline & triage (~1.5 h)

- [ ] `project/.env` from `.env.example`; set `GEMINI_API_KEY`; confirm `GEMINI_MODEL=gemini-2.5-flash`.
- [ ] Clean boot: delete `project/db/app.db` + `chroma_store/` → `streamlit run project/ui/app.py` → login `demo1/demo1pass`. Auto-seed + auto-ingest must succeed (this is what a Saturday restart looks like).
- [ ] One LLM sanity turn in chat; on a booking message, check logs for the Pydantic-AI path marker.
- [ ] Subscribe your phone to the ntfy topic; confirm one real push.
- [ ] Verify the four demo linchpins: emergency regex fires · Dr. Sunil Perera tomorrow-10:00 conflict → alternatives · medicine query sorts by cost+distance after setting city · demo1 near-due reminder fires.
- [ ] Speed-walk the demo script (Section D) once, badly; write every wart into a `TRIAGE.md` scratch list, mapped to Phase 1 items.

**Exit:** clean boot works with key; you know exactly what's ugly.

---

## Phase 1 — Demo-critical polish (~4 h, priority-ordered — cut from the bottom)

1. **Chat first impression:** welcome/empty state advertising capabilities — *"Try: I have chest pain · Book Dr. Silva tomorrow 10am · Price of Panadol"* — and meaningful spinner text.
2. **Medicine table:** LKR formatting, distance to 1 decimal, out-of-stock as a visible badge, cheapest row obvious. Column order: Pharmacy → Total → Distance → Items → Missing. *(This panel is on screen the longest — worth the time even though it was Nisal's.)*
3. **Booking success state:** unmistakable confirmation card (doctor, date, fee, "push sent"). Slot-taken → alternatives flow reads clearly.
4. **Sidebar grouping:** labeled sections (Profile / Language / Location / Family / Reminders / Logout) + copyable ntfy topic with a one-line "family subscribes at ntfy.sh/…" hint.
5. **Prescription flow:** number the steps visibly — *1 Upload/paste → 2 Confirm text → 3 Compare pharmacies*. The confirm gate should look like a gate.
6. **Thread persistence visible:** after logout→login, past conversations obviously reappear in the sidebar list.
7. **30-min i18n spot-check only:** login demo3 (si) and demo4 (ta), walk the panels, fix only what's visibly broken. No catalog sweep.
8. **30-min README pass:** fix headline drift in this repo's `Readme.md` (single `models.py`, `Conversation` table, `gemini-2.5-flash`, remove references to nonexistent files).

**Exit:** joint click-through of the full demo script looks clean; pytest green; commit.

---

## Phase 2 — Defense pack + teammate sync (~2 h)

1. **Redraw the architecture diagram (top priority).** The report's Figure 8.1 is unreadable and evaluators ask on the diagram directly. One clean Mermaid/draw.io drawing: six layers + the chat-turn request flow (viva guide §1.5–1.6 is the source of truth). Export `docs/architecture.png`; keep it open in a tab Saturday.
2. **Write `docs/DEFENSE.md`** — copy Sections A–C + E below into it verbatim; this is the file everyone memorizes.
3. **Send the teammate prep pack TODAY** (they attend; they must not improvise):
   - `MedBridge_Viva_Guide.md` with assignments: everyone Part 1 + §1.11 + Part 4; Thevindu Part 3-B; Nisal Part 3-C; Chanupa Part 3-D.
   - `docs/DEFENSE.md` (the API/platform story, security/PDPA, Streamlit/scope framing, drift list).
   - The demo script (Section D) with the *"who narrates what"* column.
   - Ask each to reply with a ✅ after reading — chase anyone silent by tonight.

**Exit:** diagram exists; DEFENSE.md exists; pack sent.

---

## Phase 3 — Supplier portal concept demo (**hard timebox 3 h — start only if Phases 0–2 are done**)

**Why:** converts the "your data is fake / where do APIs come from" defense into a live proof of the two-sided platform model, and directly hits the commercial-viability criterion.

**Spec (keep it this small):**
- New file `project/ui/supplier_portal.py`. Run: `streamlit run project/ui/supplier_portal.py --server.port 8502`.
- Reuses `project.db.db.get_conn()`. **No schema changes, no auth** (optional `SUPPLIER_PASSCODE` env gate). Banner: *"Supplier Portal — concept demo · SEED data"*.
- **Tab 1 — Pharmacy:** selectbox of pharmacies → table of that pharmacy's `PharmacyMedicinePrice` rows → edit price (number input) + toggle in-stock → UPDATE row.
- **Tab 2 — Hospital:** selectbox of doctors → list existing `AppointmentSlot`s → add slot (date + time) → INSERT (catch the UNIQUE violation with a friendly "slot already exists").
- **Scripted demo moment (this is the payoff):** seed has **Losartan 50mg out of stock at Union Chemists**. In the portal, toggle it in-stock → switch to the patient app → ask for Losartan prices → Union Chemists now appears. Say: *"That's the two-sided platform: suppliers publish, patients see it — no third-party API dependency, because the platform is the source of truth."*

**Fallback rule:** if it isn't demoable at the 3-h mark, `git stash`, and the Section B script + diagram carry the story alone. A half-broken feature is worse than a crisp explanation. Do **not** let this phase eat Phase 4.

---

## Phase 4 — Record, rehearse, drill (~2 h, Friday evening)

1. **Backup recording:** silent 2–3 min screen capture of the full happy path (include the portal moment if built). If Streamlit/key/network dies Saturday, you narrate over this instead of debugging live.
2. **Dress rehearsal #1, timed:** full demo ≤ 12 min including talking.
3. **Self-drill the Q&A bank** (Section F) out loud — especially the API/platform story, the Streamlit/scope framing, and the drift list. Weak answers → 20 min re-reading the relevant guide section.
4. Message the team the final demo order + timing and confirm everyone knows their narration slot.

---

## Phase 5 — Saturday, ~1 h before the viva

- Fresh clean boot (delete `app.db` + `chroma_store`, start app, login) ≥ 45 min before the slot; leave running. Start the supplier portal on 8502 if built.
- Pre-open tabs: patient app · supplier portal · ntfy topic · `docs/architecture.png` · ER + use-case diagrams · `docs/DEFENSE.md` · backup recording. Phone charged and subscribed.
- One fast silent run of the demo. Read the drift list (Section E) aloud once.

---

## D. Demo script (~10–12 min, online path; J drives, owners narrate)

| # | Action | Narrator | Key line |
|---|---|---|---|
| 1 | Intro (30 s) | J | "A healthcare *navigator*, never a diagnoser — five agent groups behind one trilingual chat, free-tier only, every AI feature has a deterministic fallback." |
| 2 | `I have severe chest pain and can't breathe` → confirm → tel:1990 + phone push | J | "Emergency screening is pure regex and runs *before* any LLM — zero latency on the safety path." |
| 3 | `Book me with Dr. Sunil Perera tomorrow at 10:00` → alternatives → book → push | Thevindu | "Pydantic AI proposes via typed SQL tools; only deterministic code writes the booking, atomically." |
| 4 | `I need prices for Panadol and Amoxicillin` | Nisal | "RAG-grounded matching with an edit-distance precision guard; sorted by total cost then distance." |
| 5 | *(if built)* Supplier portal: toggle Losartan in-stock at Union Chemists → re-query patient side | J | "Two-sided platform: suppliers publish, patients see it — the platform is the source of truth, no API dependency." |
| 6 | Upload sample report → specialist panel → moderator | Chanupa | "Three specialists in separate threads, no shared state — independence is structural; the disagreement list can never be empty, by code." |
| 7 | Prescription photo → OCR → confirm gate → compare | Nisal | "Nothing happens until the human confirms; dosage is only ever shown verbatim." |
| 8 | Switch to demo3 (Sinhala), one turn · then `come back in 2 weeks` → reminder push | J | "Trilingual + voice; reminders are regex, idempotent, and yield to booking intent." |
| Close | — | J | "Turn the key off and this entire demo still runs on deterministic fallbacks. Structural safety, graceful degradation." |

**Contingencies:** Gemini 429 → fallbacks engage automatically; narrate as designed behavior, never apologize. App crash → backup recording. ntfy silent → show `NotificationLog` ("every attempt is audited").

---

## A. Defense: the third-party API question

**Q: "Why is pharmacy/doctor/slot data in your own schema? Shouldn't that come from third-party APIs?"** — answer in three moves:

1. **Split the schema.** `User`, `ChatMessage`, `Appointment`, `Prescription`, `FutureVisitReminder`, `MedicalReport`, `NotificationLog` are user-owned system-of-record tables — correct production design, not mock.
2. **Name the reality.** Sri Lanka has no public pharmacy-stock API and no open channeling API (eChannelling/Doc990 are closed) — that fragmentation *is* the domain's problem statement, and the rules mandated free tier. Catalog tables hold curated seed data labeled `SEED DATA — not live` in files, logs, and UI.
3. **Show the seam.** Agents only call typed tools (`find_doctors()`, `nearest_alternatives()`, `quotes_for()`, `retrieve()`); a real data source replaces a tool body, nothing above the data layer changes.

## B. Defense: the two-sided platform model (the deeper answer — and the portal demo's script)

- **Suppliers publish INTO us; we fetch nothing.** Same model as eChannelling (doctors onboard; its DB *is* the booking system) and PickMe (restaurants manage their own menus). The absence of open APIs is *why* the marketplace model is the right design — an API-dependent product would be hostage to systems that don't exist; the supplier network is the moat.
- **Pharmacy flow:** merchant account → price list against the master `Medicine` catalog → one-tap stock updates → writes the same `PharmacyMedicinePrice` rows the seed writes today. Chains get POS-sync B2B adapters later; gaps bridged by crowdsourced availability reports (suggested by the domain brief itself).
- **Hospital flow:** admin registers `Facility`/`Doctor`, publishes slot templates → `AppointmentSlot` rows. **Our atomic booking is the authoritative booking** — `Appointment` is a real system-of-record, not user-side tracking of someone else's booking.
- **What's missing for production is only the supply side** — supplier accounts + dashboard writing to tables we already have. The seed loader stands in for the supplier portal, not for a missing API. *(The port-8502 portal makes this literal.)*
- **Cold start:** free digital storefront + foot traffic for suppliers; launch with one anchor chain / Osu Sala network; freshness labels ("updated 2 h ago") and honest "call to confirm" degradation instead of fake real-time stock.

> 30-second script: *"In production, MedBridge is a two-sided platform — the model eChannelling and PickMe used, because Sri Lanka has no open channeling or pharmacy-stock APIs. Suppliers publish their own prices, stock, and slots through a supplier portal, so our database is the system of record and our atomic booking is the real booking. Our schema already is that supplier-published catalog, and agents consume it only through typed tools — a row from the seed script, a pharmacist's dashboard, or a future POS-sync adapter is indistinguishable above the data layer."*

## C. Defense: why Streamlit / why prototype stage (memorize — this protects scope)

- **Constraint answer:** 12-hour overnight hackathon → pure-Python UI, no build chain; the panel contract let four people work in parallel. Streamlit is the industry-standard demo layer for AI/ML systems — the correct choice, not a shortcut.
- **Architecture answer:** presentation is a thin shell; agents, tools, RAG, and DB know nothing about Streamlit. A FastAPI + React/mobile front-end swaps exactly one layer of the diagram *(point at the diagram while saying this)*.
- **Scope framing:** *"This is a validated prototype, deliberately. It validates the three risky things — multi-agent orchestration, the structural safety model, and the marketplace data layer. Everything else has a known production path: FastAPI backend, React/mobile clients, Postgres, signed sessions, containerized deploy."* Anything not included is roadmap, not gap.
- **Hosting:** demos run locally / on Streamlit Community Cloud; production hosting is a different stack, out of prototype scope by design.

## E. Defense: security, privacy, compliance & drift (unchanged essentials)

**Lead with:** bcrypt everywhere (incl. seed users) · full session wipe on logout · disclaimers injected by UI code, not prompts · symptom→specialty only, never disease · OCR confirm gate · dosage verbatim from catalog only · every push audited in `NotificationLog` · `.env` gitignored, leaked key rotated during the event · every query scoped by `user_id`.

**Volunteer before they find it:** `?uid=` remember-me is unsigned (demo-grade; production = signed sessions/JWT) · ntfy topics guessable (production = authenticated push) · SQLite unencrypted at rest (production = Postgres + encryption + TLS + RBAC) · no login rate limiting.

**Compliance card:** production handles health data — a *special category* under **Sri Lanka's Personal Data Protection Act No. 9 of 2022** (consent, purpose limitation, breach notification, safeguards); same posture as GDPR Art. 9. "The prototype's structural safety choices are the seeds of that compliance posture."

**Drift list (evaluators read the frozen repo — own these):** report claims Docker/CI/DEMO.md that aren't in the repo → "written from the plan; didn't land in the 12 hours — the fallbacks and tests did" · README `models/` package vs real single `models.py` · `ChatSession` vs real `Conversation` · README `gemini-1.5-flash` vs code `gemini-2.5-flash` · chatbot docstring says CrewAI routing but it's a direct timed Gemini JSON call (why: CrewAI added ~5 s and retried 429s into 30–60 s hangs; CrewAI genuinely runs the specialist panel).

## F. Q&A drill bank (Friday night, out loud)

1. Walk me through your architecture diagram. *(Six layers, then the chat-turn lifecycle — guide §1.5–1.6.)*
2. Where does the LLM sit, and what happens when it's down? *(LLM/no-LLM table, guide Part 4.)*
3. Why Streamlit / where's the real frontend? *(Section C, all three layers of the answer.)*
4. Your data is fake — what's real? *(Sections A + B; if the portal is built, offer to show it.)*
5. How do you protect medical records? *(Section E — lead with controls, volunteer limitations, name PDPA.)*
6. Prove you wrote this. *(Your files: walk `ground_specialty()` and the heuristic-first router line-by-line; know `git log --author`.)*
7. What breaks at 10,000 users? *(SQLite writer lock → Postgres; Streamlit sessions → stateless API; ntfy → FCM; free tier → paid/self-hosted.)*
8. Name your non-functional requirements. *(Security · privacy/PDPA · reliability = graceful degradation · performance = heuristic-first <3 s · usability = trilingual + voice · maintainability = 52 offline tests + panel contract · cost = free-tier only.)*
9. Two more weeks? *(Supplier onboarding behind existing tool seams, signed sessions, Postgres, retrieval-quality evaluation, one pharmacy-chain pilot.)*
10. Why does the demo differ from the frozen repo? *(Rule-#4 one-liner, top of this file.)*

---

## Definition of done

App boots clean from scratch with the key · demo ≤ 12 min, rehearsed and recorded · teammate pack sent and acknowledged · architecture diagram redrawn and open in a tab · you can deliver Sections A–C and E without notes · pytest green on `viva-prep` · supplier portal either demoable or cleanly stashed.
