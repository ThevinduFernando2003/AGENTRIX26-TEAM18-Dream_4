# MedBridge AI

Multi-agent healthcare navigator built for **AgenTrix 2026** by Team
Dream_4 (TEAM18). Patients log in, chat with a memory-backed triage
agent, get rule-based emergency screening, book doctor appointments
with conflict handling, and compare medicine prices across nearby
pharmacies.

**Never produces a medical diagnosis.** Every symptom / medicine /
report surface carries:

> This is an AI-generated observation, not a medical diagnosis. Please
> consult a licensed physician or pharmacist.

All facility, doctor, slot, pharmacy and price data is **SEED / MOCK
data**, labelled in the UI and the seed files.

---

## Tier 1 scope (this build)
- Signup / login (bcrypt-hashed passwords)
- Basic Agent Chatbot with persistent chat history (CrewAI + Gemini)
- Rule-based emergency screener (runs **before** any LLM call)
- Emergency flow: `tel:1990` link + ntfy.sh push to family contact
- Booking Agent (Pydantic AI typed responses) with full-slot fallback
- Medicine Tracker (text-input) — pharmacy comparison by total cost
  and distance (live browser geolocation, manual entry fallback)

Tier 2 (Specialist Panel + Moderator, prescription OCR) and Tier 3
(voice, i18n, future-visit reminders) are deliberately out of scope
for this build.

---

## Setup

Python 3.10+ recommended.

```bash
pip install -r project/requirements.txt
cp project/.env.example project/.env
# Edit project/.env and set GEMINI_API_KEY (free tier).
```

Required env vars (see `project/.env.example`):

| Variable             | Default            | Purpose                                |
| -------------------- | ------------------ | -------------------------------------- |
| `GEMINI_API_KEY`     | _(required)_       | Free-tier Gemini key for the chatbot   |
| `GEMINI_MODEL`       | `gemini-1.5-flash` | Model id                               |
| `NTFY_TOPIC_PREFIX`  | `medbridge-demo`   | Per-user topic = `{prefix}-{user_id}`  |

> If `GEMINI_API_KEY` is missing, the chatbot falls back to a
> deterministic keyword router so the rest of the demo still works.

Initialise the DB and load seed data:

```bash
python -m project.db.db
```

Run the app:

```bash
streamlit run project/ui/app.py
```

---

## ntfy.sh push notifications

Topic scheme per user: `<NTFY_TOPIC_PREFIX>-<user_id>`. The sidebar
shows the topic; have the family member subscribe at
`https://ntfy.sh/<topic>` (free, no signup) before triggering an
emergency for the demo.

---

## Demo walkthrough

After `streamlit run`:

1. Sign up `demo / demopass` (or log in as the seeded `demo1 / demo1pass`).
2. Sidebar: click the location button (or enter Colombo coordinates
   manually). Copy the ntfy topic and subscribe in another tab.
3. Chat: `"I have a mild headache."` → normal triage reply, history
   persists.
4. Chat: `"I have severe chest pain and can't breathe."` → red
   emergency panel. Confirm → `tel:1990` button + push arrives in your
   ntfy tab.
5. Chat: `"Book me with Dr. Sunil Perera tomorrow at 10:00"` (that
   slot is intentionally seeded full) → agent returns 3–5 nearby
   alternative slots. Click **Book** on one → confirmation + ntfy push.
6. Chat: `"I need prices for Panadol and Amoxicillin"` → sorted
   pharmacy comparison with totals and distance.
7. Refresh the page; the chat history reloads from SQLite.

---

## Folder layout

```
project/
├── agents/
│   ├── basic_chatbot.py     # CrewAI orchestrator + memory
│   ├── booking_agent.py     # Pydantic-typed booking with alternatives
│   ├── medicine_tracker.py  # Text-input pharmacy comparison
│   └── emergency.py         # Pure-regex screen — no LLM
├── db/
│   ├── schema.sql           # 17 tables
│   ├── db.py                # get_conn(), init_db()
│   └── seed.py              # Idempotent SEED loader
├── kb/                      # Hand-built seed JSONs (SEED — not live)
├── notifications/
│   └── ntfy_client.py       # HTTP POST to ntfy.sh + NotificationLog
├── ui/
│   ├── app.py               # Streamlit entry
│   └── auth.py              # bcrypt login / signup
├── models.py                # All Pydantic models
├── requirements.txt
├── .env.example
└── README.md
```

---

## Hard constraints honoured

- ✅ Only **free-tier** APIs (Gemini free tier, ntfy.sh free topics).
- ✅ All orchestration is real Python (CrewAI + Pydantic AI). No
  n8n / Zapier.
- ✅ Never produces a diagnosis. Disclaimer rendered by the UI, not
  the LLM.
- ✅ Passwords hashed with `passlib[bcrypt]`. Never plaintext, even
  for seed users (the loader hashes them on insert).
- ✅ Emergency dialling is rendered as a `tel:1990` link (opens the
  device's native dialer) — no paid telephony.
- ✅ Medicine Tracker never invents dosage; only `reference_dosage_text`
  from the seed catalog is shown.
- ✅ All seed JSONs carry a `"_note": "SEED DATA — not live"` label
  and the loader echoes it on insert.
