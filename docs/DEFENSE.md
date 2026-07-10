# MedBridge AI — Viva Defense Sheet

Memorize this. Every answer here is honest, short, and safe to say on record.
Companion diagrams: [architecture.html](architecture.html) (open in a tab).

---

## 1. The 30-second opener

> "MedBridge AI is a healthcare **navigator**, never a diagnoser — five agent groups
> behind one trilingual chat. Safety is **structural**: emergency screening is pure
> regex before any LLM, disclaimers are injected by UI code, OCR needs human
> confirmation, and booking writes are atomic SQL. Every AI feature has a
> deterministic fallback, so the entire demo runs even with no API key."

---

## 2. "Why is doctor/pharmacy data in YOUR database? Where are the third-party APIs?"

Answer in three moves:

1. **Split the schema.** `User`, `ChatMessage`, `Appointment`, `Prescription`,
   `FutureVisitReminder`, `MedicalReport`, `NotificationLog` are **user-owned,
   system-of-record tables** — production-correct by design. No third party stores
   a patient's bookings or chat history for us.
2. **Name the reality.** Sri Lanka has **no public pharmacy-stock API and no open
   channeling API** (eChannelling/Doc990 are closed). That fragmentation *is* the
   domain's problem statement. Catalog tables hold curated data labeled
   `SEED DATA — not live` in the files, the logs, and the UI.
3. **Show the seam.** Agents never touch those tables directly — they call typed
   tools (`find_doctors()`, `nearest_alternatives()`, `quotes_for()`, `retrieve()`).
   A real data source replaces a tool body; nothing above the data layer changes.

## 3. The production model: a two-sided platform (the deeper answer)

> "In production, MedBridge is a **two-sided platform** — the same model
> eChannelling and PickMe used, precisely because no open APIs exist here.
> **Suppliers publish INTO us; we fetch nothing.**"

- **Pharmacy flow:** merchant account → price list against our master `Medicine`
  catalog → one-tap stock updates → writes the same `PharmacyMedicinePrice` rows
  the seed writes today. Chains get POS-sync B2B adapters later; coverage gaps are
  bridged by crowdsourced availability reports (suggested by the domain brief itself).
- **Hospital flow:** admin registers `Facility`/`Doctor`, publishes weekly slot
  templates → `AppointmentSlot` rows. **Our atomic booking IS the authoritative
  booking** (like an eChannelling booking) — `Appointment` is a real system of
  record, not a mirror of someone else's system.
- **What's missing for production is only the supply side** — supplier accounts and
  a dashboard writing to tables we already have. The seed loader stands in for the
  supplier portal, not for a missing API. *(If the port-8502 supplier portal demo is
  built: show it here — toggle Losartan in-stock at Union Chemists, re-query.)*
- **Cold start ("why would a pharmacy join?"):** free digital storefront + foot
  traffic from patients already searching for their medicine; launch via one anchor
  chain or the state Osu Sala network; show "updated 2 h ago" freshness labels and
  degrade to "call to confirm" instead of faking real-time stock.
- **Why not integrate anyway?** An API-dependent product is hostage to systems that
  don't exist. The platform model removes the dependency — and the supplier network
  becomes the moat.

## 4. "Why Streamlit? Where's the real frontend?" (scope armor)

1. **Constraint:** 12-hour overnight hackathon → pure-Python UI, no build chain;
   the panel contract let four people work in parallel without merge conflicts.
   Streamlit is the industry-standard demo layer for AI/ML systems.
2. **Architecture:** presentation is a thin shell — agents, tools, RAG, and DB know
   nothing about Streamlit. A FastAPI + React/mobile front-end swaps exactly one
   layer of the diagram *(point at it)*.
3. **Declared scope:** "This is a **validated prototype, deliberately**. It
   validates the three risky things — multi-agent orchestration, the structural
   safety model, and the marketplace data layer. Everything else has a known
   production path: FastAPI backend, React/mobile clients, Postgres, signed
   sessions, containerized deploy." Anything not included is roadmap, not gap.
4. **Hosting:** demos run locally / Streamlit Community Cloud; production hosting
   is a different stack, out of prototype scope by design.

## 4b. "The emergency button is a gimmick — a person with chest pain just dials 1990"

Agree with the premise, then flip it:

> "Correct — someone who *knows* they're having a heart attack dials 1990 directly.
> This feature is for the patient who **doesn't recognize the danger** — they came
> to chat precisely because they think it's minor. 'A rash and my throat feels
> tight' is anaphylaxis onset; epigastric pain 'like gastritis' is how silent
> heart attacks present; stroke signs get typed as 'feeling weak and tired'."

Then the three supporting points:
1. **Duty of care (strongest):** any system that accepts symptom text must never
   act normally on a red-flag input. If a user types "crushing chest pain" and the
   bot calmly offers a Tuesday cardiology slot, *that* is the safety failure. The
   screen guarantees the system cannot book-as-usual through an emergency.
2. **The family push is what the user can't do themselves** — one tap notifies a
   preset contact while they're distressed or alone. And 1990 awareness is
   incomplete (rural users, tourists).
3. **Multi-authority routing is roadmap, nearly free:** the screener already labels
   every match with a category (anaphylaxis, chest pain, self-harm, poisoning…).
   Mapping category → hotline is a lookup table: 1990 Suwa Seriya, 119 Police,
   1926 NIMH mental-health line for self-harm, Poison Information Centre.
   *"The categories exist today; multi-authority routing is a dictionary away."*

**"But the screen runs on every message — extra cost?"** — measured answer:
> "It's 32 compiled regexes running in about **32 microseconds**, in-process, no
> network, no API cost. The LLM call it guards costs 2–8 *seconds* and quota —
> the screen is ~100,000× cheaper than the thing it protects. That's exactly why
> it runs first on 100% of messages: the cheapest check guards the biggest risk."

## 4c. How routing + fallbacks actually work (say it simply)

**Routing ladder — cheapest first:**
1. Emergency regex (32 µs) → match ends the turn safely.
2. Reminder regex — *skipped when booking verbs are present*, so "book me in
   2 weeks" books instead of setting a reminder.
3. Keyword heuristic: book/appointment/consult → booking · medicine/pharmacy/price
   → medicine · report/scan/ECG → report review. **A hit here never calls the LLM.**
4. Only genuinely ambiguous messages spend ONE LLM JSON call — 8 s timeout,
   zero retries; any failure falls back to a friendly general reply.

> "Unambiguous intents never wait on a model. The LLM is reserved for messages
> where a thoughtful reply matters — it can only make answers better, never
> block them."

**Fallback law: the LLM can enhance, never gate.** One availability check plus
try/except on every online call, then a deterministic plan B per feature:

| Feature | With LLM | Without / on failure |
|---|---|---|
| Chat routing | JSON classifier | Keyword heuristic |
| Booking | Pydantic AI proposes | Deterministic SQL engine (the source of truth; only `book()` writes) |
| Specialist panel | 3 CrewAI agents | 3 stubs that differ by specialty (moderator still gets disagreement) |
| Moderator | LLM synthesis | Flag intersection = agreement; differences = disagreement; disclaimer by code |
| Medicine match | — | Substring → difflib fuzzy → RAG (returns `[]` offline, never raises) |
| Translation | LLM | English passthrough |
| Voice / OCR | STT / Vision | Honest "unavailable" → type / paste path, same confirm gate |

> Closing line: "Turn the API key off and this entire demo still runs."

## 4d. Location & distance: prototype vs production

- **Today:** browser geolocation or a city picker → **haversine** straight-line km.
  Why: deterministic, free, offline, and good enough to *rank* nearby pharmacies.
- **Production (mobile app):** native GPS for precise location + Google Maps
  Routes / Distance Matrix for real road distance and travel time (paid API —
  fine in production, excluded from the free-tier competition build by rule).
- **The seam:** the swap happens inside the quote-sorting code; agents, tools,
  and UI don't change — same pattern as every other integration seam.

## 5. Security, privacy & compliance

**Lead with what we actively do:**
- bcrypt for every password, including seed users — no plaintext anywhere.
- Full session wipe on logout (fixed a cross-user leak in Phase 1) — session isolation.
- Disclaimers injected by **UI code**, never by the LLM — a malformed generation
  cannot drop them. Symptom → *specialty* only, never a disease.
- OCR confirm gate: no pharmacy action on unconfirmed machine-read text; dosage
  is shown verbatim from the catalog only.
- Every notification attempt audited in `NotificationLog`.
- `.env` gitignored; a leaked key was rotated during the event itself.
- Every query is scoped by `user_id`; cascade deletes on user-owned data.

**Volunteer the limitations before they find them:**
- The `?uid=` remember-me is **unsigned** → demo-grade; production = signed
  sessions/JWT.
- ntfy topics are guessable → production = authenticated push (FCM) or ntfy tokens.
- SQLite is unencrypted at rest → production = Postgres, encryption at rest, TLS,
  role-based access.
- No login rate limiting / lockout yet.

**The compliance card (say the name):**
> "A production version handles health data — a *special category of personal data*
> under **Sri Lanka's Personal Data Protection Act, No. 9 of 2022** — requiring
> consent, purpose limitation, breach notification, and security safeguards; the
> same posture as GDPR Article 9. The prototype's structural safety choices are
> the seeds of that compliance posture."

## 6. Non-functional requirements (name them when asked)

Security (bcrypt, session isolation) · Privacy/compliance (PDPA, per-user scoping)
· Reliability (graceful degradation — every AI path has a deterministic fallback)
· Performance (heuristic-first routing < 3 s; emergency path zero-latency)
· Usability/accessibility (trilingual UI + voice in/out)
· Maintainability (52 offline tests, lint, one-file-per-panel contract)
· Cost (free-tier design: Gemini free tier, ntfy.sh, gTTS, local embeddings).

## 7. Doc-vs-code drift — own it before they find it

- Report claims Docker/CI/DEMO.md → "written from our plan; those didn't land in
  the 12 hours — the deterministic fallbacks and the test suite did."
- README shows a `models/` package → reality is a single `models.py` (consolidated).
- `ChatSession` in docs → actual table is `Conversation` (renamed).
- README said `gemini-1.5-flash` → code default is `gemini-2.5-flash`.
- Chatbot docstring says CrewAI routing → replaced with one direct, timed JSON
  call (CrewAI added ~5 s and retried 429s into 30–60 s hangs). CrewAI genuinely
  runs the specialist panel + moderator.

## 8. "Why does the demo differ from the frozen repo?"

> "The frozen repo is our untouched 12-hour state. Per rule 4 we continued in a
> separate polish repository — the architecture is identical; the changes are
> visual polish, doc fixes, and demo assets."

**If asked which model the demo is calling right now:** be straight —
> "The 12-hour build runs exclusively on the Gemini free tier — that's the frozen
> repo you reviewed. In the polish repo we added a one-line provider abstraction so
> we could rehearse without burning free-tier quota; the competition solution's
> design and the reviewed code are Gemini free tier."
*(Lowest-risk option remains demoing on a fresh free Gemini key: `LLM_PROVIDER=gemini`
+ key in `.env` — decide before Saturday.)*

## 9. Rapid-fire answers

- **"Prove you wrote this."** Name your files, walk one function line-by-line,
  show `git log --author=<you>`.
- **"What breaks at 10,000 users?"** SQLite writer lock → Postgres; Streamlit
  sessions → stateless API + queue; ntfy → FCM; free tier → paid/self-hosted models.
- **"What's real vs mock?"** Real: orchestration, agents, RAG, atomic booking,
  safety gates, auth, i18n, notifications. Mock (labeled): catalog rows behind
  swappable tools.
- **"LLM down mid-demo?"** Fallbacks engage automatically — heuristic router, stub
  panel opinions, English passthrough, paste-text OCR. *Narrate it as designed
  behavior, never apologize.*
- **"Two more weeks?"** Supplier onboarding portal behind the existing tool seams,
  signed sessions, Postgres, retrieval-quality evaluation, one pharmacy-chain
  pilot, multi-authority emergency routing (category → 1990/119/1926 lookup),
  and a mobile app with native GPS + Maps road-distance routing.
