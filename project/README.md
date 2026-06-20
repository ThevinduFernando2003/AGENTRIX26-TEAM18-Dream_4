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

## Tier 1 scope
- Signup / login (bcrypt-hashed passwords)
- Basic Agent Chatbot with persistent chat history (CrewAI + Gemini)
- Rule-based emergency screener (runs **before** any LLM call)
- Emergency flow: `tel:1990` link + ntfy.sh push to family contact
- Booking Agent (Pydantic AI typed responses) with full-slot fallback
- Medicine Tracker (text-input) — pharmacy comparison by total cost
  and distance (live browser geolocation, manual entry fallback)

## Tier 3 scope
- **Sinhala / Tamil / English UI** — a static `i18n` catalog covers
  every visible label; the user's preferred language flips it.
- **Voice input** — Gemini `gemini-1.5-flash` speech-to-text via
  `st.audio_input`. Disabled gracefully when `GEMINI_API_KEY` is
  absent.
- **Voice output** — gTTS (free, no API key) plays each assistant
  reply in the user's preferred language when the sidebar toggle is on.
- **Free-form reply translation** — when the user prefers Sinhala or
  Tamil, the chatbot's English reply is translated via Gemini before
  persistence. Cached per process to spare the free-tier quota.
- **Future-visit reminders** — rule-based regex inside the chatbot
  detects "come back in 2 weeks / next month / on YYYY-MM-DD",
  persists a `FutureVisitReminder` row. Sidebar **🔔 Check my
  reminders** button finds rows due within 7 days and fires an ntfy
  push per reminder; `notified=1` flips on success, idempotent on
  re-click.

## Tier 2 scope
- **Specialist Panel** — three CrewAI agents (cardiology, internal
  medicine, radiology) read the SAME report **independently**. Each
  builds its own `LLM`/`Agent`/`Crew` and runs in a separate thread —
  there is no shared state, by construction.
- **Moderator Agent** — synthesises the three opinions into a
  `ConsensusReport`. `points_of_disagreement` is **never silently
  empty** — a code-level guard in `agents/moderator.py:_ensure_invariants`
  injects "No material disagreement among the panel." rather than
  leaving the field blank.
- **Prescription OCR + confirmation gate** — Gemini Vision transcribes
  a prescription photo, the user **must** confirm the editable text
  before any pharmacy lookup runs. Falls back gracefully to a
  text-paste path when `GEMINI_API_KEY` is absent.
- Two new ntfy notification types wired in:
  `report_review_complete` (panel ready) and
  `prescription_confirmed` (after the user OKs OCR).

Tier 3 (voice, full Sinhala/Tamil UI strings, future-visit reminder
scheduling) is deliberately out of scope for this build.

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

### Tier-2 demo additions

8. Chat: `"Can you review my ECG report?"` → chatbot routes to
   `report_review` and the **📄 Specialist Panel** expander opens.
9. Pick `report_ambiguous_findings.txt` from the sample dropdown,
   click **Run Specialist Panel**. Three columns render with
   independent findings, varying confidence bars, and concern flags.
   Below them the **Moderator** lists points of agreement and
   disagreement — disagreement entries are rendered as warnings so
   they aren't smoothed visually either.
10. A `report_review_complete` ntfy push arrives on your subscribed
    topic.
11. Open the **💊 Prescription photo** expander, upload a JPG/PNG of
    a prescription. Gemini Vision transcribes it; the text appears
    in an editable text area with the question
    *"Is this exactly what's written on your prescription?"*. Only
    after **✅ Yes — search pharmacies** does the pharmacy comparison
    run. SQLite shows `Prescription.user_confirmed = 1`.
12. Without `GEMINI_API_KEY`, the prescription expander shows an
    honest "Gemini Vision unavailable" warning and the panel-review
    flow falls back to deterministic stub opinions. The disagreement
    guard still fires.

### Tier-3 demo additions

13. Log in as a seeded Sinhala/Tamil user (`demo3` / `demo3pass` for
    Sinhala, `demo4` / `demo4pass` for Tamil). Sidebar, title and
    most labels flip to that language. Chat replies are translated
    via Gemini when an API key is set; without a key, the English
    reply is shown unchanged.
14. Chat: `"Doctor asked me to come back in 2 weeks"` → rule-based
    detector fires **before** the LLM, the assistant acknowledges
    in the user's language, and a `FutureVisitReminder` row appears
    in SQLite with `target_date_or_month` ≈ today + 14 days.
15. Sidebar → **🔔 Check my reminders**. Within 7 days → button to
    push appears. Click → ntfy push fires, `notified=1`, log row in
    `NotificationLog`. Re-click → 0 sent (idempotent).
16. Toggle **🔊 Speak assistant replies** on. The next assistant
    reply gets an inline mp3 audio widget — Sinhala / Tamil / English
    voiced via gTTS.
17. Open **🎙️ Voice input** (with `GEMINI_API_KEY` set), record a
    short clip in your preferred language, click **Transcribe &
    send**. The text appears as if you'd typed it; the chatbot
    handles it normally. Without a key, the expander shows a clear
    "voice input unavailable" message.

---

## Folder layout

```
project/
├── agents/
│   ├── basic_chatbot.py     # CrewAI orchestrator + memory + reminder regex
│   ├── booking_agent.py     # Pydantic-typed booking with alternatives
│   ├── medicine_tracker.py  # Text-input + OCR-confirm pharmacy comparison
│   ├── emergency.py         # Pure-regex screen — no LLM
│   ├── specialist_panel.py  # 3 independent CrewAI specialists (Tier 2)
│   ├── moderator.py         # Consensus + structural disagreement guard
│   ├── vision_ocr.py        # Gemini Vision prescription OCR helper
│   └── reminders.py         # Due-window + ntfy push (Tier 3)
├── i18n/
│   ├── translate.py         # Static catalog + Gemini dynamic translation
│   ├── tts.py               # gTTS wrapper
│   └── stt.py               # Gemini speech-to-text
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
