# MedBridge AI — Phase 3 Handoff (continue on another device)

This document handed off Phase 3 mid-flight. **All steps (1–10) are now complete
and verified** — the remaining work (Steps 5–10) was finished on the
`phase3-steps5-10` branch (cut from `Test`). It is kept here as the execution
record.

> **Step 0 (unplanned blocker, fixed first):** the `Test` branch was missing
> `project/rag/__init__.py` and the `medicine`/`prescription`/`__init__` panels —
> the PR#5 revert (`147bb0d`) had dropped them, so the app wouldn't boot and
> pytest had collection errors. These were restored from `nisal` (imports are
> compatible with Test's single-file `project/models.py`) before Steps 5–10.

> Decisions locked for this phase (do not re-litigate):
> - **Host:** Streamlit Community Cloud (full-AI: a rotated/billed `GEMINI_API_KEY`
>   is supplied as a Cloud secret). Vercel is NOT used — it can't run Streamlit.
> - **Scope:** all four PLAN1 lanes of Phase 3 + deployment + a theme/layout UI polish.
> - Seed/mock data is intentional — **do NOT add live pharmacy/doctor APIs.**
> - The leaked Gemini key from git history is already rotated.

---

## 0. Status at a glance

| Step | Title | State |
|---|---|---|
| 0 | Restore files dropped by the PR#5 revert (`rag/__init__`, medicine/prescription panels) | ✅ done |
| 1 | Deploy scaffold (root `requirements.txt`, secrets bridge, `.gitignore`, `DEPLOY.md`) | ✅ done |
| 2 | Routing latency fix (heuristic-first + direct Gemini JSON + 8s timeout + chat spinner) | ✅ done |
| 3 | Pydantic AI booking agent fix (module-level imports + bounded timeout) | ✅ done |
| 4 | History/Timeline panel + i18n strings | ✅ done |
| 5 | Reminders demo seed + booking panel UX (+ `raw_text` passthrough to agent) | ✅ done |
| 6 | Prescription OCR sample image + voice (STT/TTS) hardening | ✅ done |
| 7 | i18n completeness + JSON regex tightening + demo seed review | ✅ done |
| 8 | Tests across all four lanes → one green `pytest` (52 passed) | ✅ done |
| 9 | UI polish pass (theme + layout) | ✅ done |
| 10 | Final E2E + deploy verify (manifest pinned to verified env; bcrypt 4.0.1) | ✅ done |

The full original plan lives in [PLAN1.md](PLAN1.md) (Phase 3 section). This file
supersedes it for execution detail.

---

## 1. Get this state onto the other device

The Step 1–4 changes may not be pushed yet. **On the current machine, commit and
push first** (work stays on the `nisal` branch, commit per step, no PR yet):

```bash
git add -A && git commit -m "Phase 3 steps 1-4: deploy scaffold, routing latency, pydantic-ai fix, history panel"
git push origin nisal
```

Then on the other device:

```bash
git clone <repo-url> && cd AGENTRIX26-TEAM18-Dream_4
git checkout nisal

# Python 3.12. Create venv and install the PINNED deploy manifest.
python -m venv .venv
.venv/Scripts/activate            # Windows (Git Bash: source .venv/Scripts/activate)
# or: source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt   # root file = pinned versions verified to work

# Secrets for local full-AI runs (gitignored, never commit):
cp project/.env.example project/.env
#   then edit project/.env and set GEMINI_API_KEY=<the rotated key>
```

Run the app / tests:

```bash
streamlit run project/ui/app.py            # http://localhost:8501
python -m pytest -q                        # offline, no key needed; must stay green
```

**Windows console note:** when running ad-hoc `python -c "...print(emoji)..."`
checks, prefix with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` or the cp1252 console
throws `UnicodeEncodeError` on emoji (the code is fine; it's only the print).

---

## 2. What Steps 1–4 changed (so you know the current baseline)

### Step 1 — Deploy scaffold
- **`requirements.txt`** (NEW, repo root): pinned deploy manifest Streamlit Cloud
  auto-detects. `onnxruntime==1.27.0` pinned explicitly (chromadb's local
  embedding backend needs it or RAG silently returns `[]`).
- **`project/ui/app.py`**: added a **secrets bridge** (`_bridge_secrets_to_env`)
  that copies `st.secrets` → `os.environ` *before* importing any project module,
  because agents read `os.environ.get("GEMINI_API_KEY")` and Cloud only exposes
  `st.secrets`. Local `.env` still wins; no-op when there's no secrets file.
- **`.gitignore`**: was ignoring all of `.streamlit/`; now `.streamlit/*` +
  `!.streamlit/config.toml` so the theme deploys but `secrets.toml` stays ignored.
- **`.streamlit/config.toml`** (NEW): starter teal/slate theme (polished in Step 9).
- **`DEPLOY.md`** (NEW): click-by-click Cloud deploy steps + secret hygiene.

### Step 2 — Routing latency fix (`project/agents/basic_chatbot.py`, `chat.py`, `translate.py`)
- Removed the CrewAI `Agent/Task/Crew` router. `_run_llm` is now a **single direct
  `google.generativeai` JSON call** (`response_mime_type=application/json`,
  `request_options={"timeout": 8}`, **no retries**) → fails fast to the heuristic.
- `handle()` is now **heuristic-first**: `_heuristic_route` runs first; booking/
  medicine/report intents skip the LLM entirely; the LLM is only called for the
  `"general"` bucket.
- `chat.py` wraps `handle()` in `st.spinner(t("chat.thinking", lang))`; user turn
  echoes immediately. Added `chat.thinking` to the catalog (en/si/ta).

### Step 3 — Pydantic AI booking agent (`project/agents/booking_agent.py`)
- **Root-cause fix:** `from pydantic_ai import Agent, RunContext` (+ `GeminiModel`,
  `GoogleGLAProvider`, `UsageLimits`) moved to **module level** in a guarded
  `try/except` (sets names to `None` + `_PYDANTIC_AI_AVAILABLE=False` offline).
  Previously these were imported *inside* `_get_booking_agent()`, so `@agent.tool`
  couldn't resolve `RunContext[BookingDeps]` against module globals →
  `NameError` → silent fallback. The agent now actually builds & runs when keyed.
- `process_agentic` passes `model_settings={"timeout": 8.0}` +
  `UsageLimits(request_limit=6)` and logs `INFO "Booking via Pydantic AI agent"`
  so logs confirm the real path. Any failure still falls back to `process()`.

### Step 4 — History panel (`project/ui/panels/history.py` NEW, `app.py`, `translate.py`)
- Read-only `render(user)` panel: merges appointments, completed report reviews,
  prescriptions, reminders and the last 15 chat turns into one chronological
  timeline (collapsed expander, rendered just above chat). 16 `history.*` catalog
  keys added in en/si/ta. (Pharmacy lookups aren't persisted, so the medicine
  flow surfaces via its `Prescription` row — documented in the module docstring.)

**Verification already passing:** `python -m pytest -q` → **12 passed**; live
offline routing classification correct for all intents; agent builds with a key
and is `None` offline; history events gather/sort/translate correctly.

---

## 3. Facts the next dev needs (don't re-derive)

- **Installed versions (`.venv`):** streamlit 1.58.0, crewai 1.9.3, chromadb 1.1.1,
  onnxruntime 1.27.0, pydantic 2.11.10, **pydantic-ai 0.4.3**, google-generativeai
  0.8.6, bcrypt 5.0.0, gTTS 2.5.4, numpy 2.4.6. Python 3.12.
- **pydantic-ai 0.4.3 API (verified):** `from pydantic_ai import Agent, RunContext`;
  `from pydantic_ai.models.gemini import GeminiModel`; `from
  pydantic_ai.providers.google_gla import GoogleGLAProvider`; `from
  pydantic_ai.usage import UsageLimits`. `ModelSettings` is a TypedDict with a
  `timeout` field; `Agent.__init__` accepts `model_settings`; `agent.run_sync(...,
  deps=, model_settings=, usage_limits=)` → `result.output`.
- **Gemini SDK pattern** (reuse for any new LLM call): `import
  google.generativeai as genai; genai.configure(api_key=...);
  genai.GenerativeModel(os.environ.get("GEMINI_MODEL","gemini-2.5-flash"))` then
  `.generate_content(prompt, generation_config={...}, request_options={"timeout":N})`.
- **Offline rule (non-negotiable):** every new LLM/voice/vision feature must
  degrade cleanly with no `GEMINI_API_KEY` (return `[]`/`""`/stub, never raise).
  `pytest` runs offline via the `no_api_key` fixture and must stay green.
- **Panel contract** (`project/ui/panels/__init__.py`): `def render(user: dict) ->
  None`, draws to the page, reads/writes `st.session_state`, never returns data.
  Chat routes to domain panels via a one-shot `st.session_state["route_request"]`.
- **i18n:** `t(key, lang, **fmt)` from `project/i18n/translate.py`; `CATALOG`
  must have `en`/`si`/`ta` for every key. `translate_dynamic(text, lang)` LLM-
  translates free-form agent text (returns input unchanged offline).
- **DB:** SQLite at `project/db/app.db`, schema in `project/db/schema.sql`, seeded
  by `project/db/seed.py::load_seed_if_empty` (**only when the User table is
  empty** — to re-seed, delete `project/db/app.db` and restart). Demo users:
  `demo1`..`demo6`, password `demo<N>pass`. `demo1`=en, `demo3`=si, `demo4`=ta.
- **Timestamps** are all SQLite `datetime('now')` (`YYYY-MM-DD HH:MM:SS`) — lexical
  sort == chronological sort.

---

## 4. Step 5 — Reminders demo seed + booking panel UX

**Goal:** the future-visit reminder demo fires a real ntfy push in ONE click, the
booking panel never looks frozen, and the Pydantic AI agent receives the user's
natural-language request (the carry-forward from Step 3).

### 5a. Seed one near-due reminder — `project/db/seed.py`
Add a seeder so `demo1` has a reminder due in ~3 days (idempotent):

```python
def _seed_reminders() -> None:
    conn = get_conn()
    row = conn.execute("SELECT user_id FROM User WHERE username = 'demo1'").fetchone()
    if not row:
        return
    uid = row["user_id"]
    if conn.execute("SELECT 1 FROM FutureVisitReminder WHERE user_id = ?", (uid,)).fetchone():
        return
    conn.execute(
        """INSERT INTO FutureVisitReminder(user_id, doctor_id, target_date_or_month, notified)
           VALUES(?, NULL, ?, 0)""",
        (uid, _resolve_date(3)),  # ~3 days out → inside the 7-day "due" window
    )
    conn.commit()
```
Call it at the end of `load_seed_if_empty()` (after `_seed_pharmacies()`).
**Re-seed:** delete `project/db/app.db` and restart the app (seed only runs on an
empty User table).

### 5b. `raw_text` passthrough to the agent — `project/agents/booking_agent.py` + `project/ui/panels/booking.py`
- Add a field to `BookingContext`:
  ```python
  @dataclass
  class BookingContext:
      user_id: int
      extracted: dict
      raw_text: str = ""      # NEW
  ```
- In `_agent_prompt`, include the natural-language request so the agent can read
  dates/doctors itself (change its signature to take the ctx, or pass `raw_text`):
  ```python
  detail = "; ".join(parts) if parts else "(no structured fields extracted)"
  raw = (ctx.raw_text or "").strip()
  extra = f'\nPatient said verbatim: "{raw}"' if raw else ""
  return f"Patient booking request — {detail}.{extra} Find and propose available slots."
  ```
- In `booking.py::_consume_route`, pass it through:
  ```python
  ctx = booking_agent.BookingContext(
      user_id=user["user_id"],
      extracted=req.get("extracted", {}),
      raw_text=req.get("raw_text", ""),     # NEW
  )
  ```
- (Optional) Extend `parse_date` to resolve weekday phrases like "next Tuesday"
  (map weekday name → next future date). Nice-to-have; the agent already returns
  real slots without it.

### 5c. Booking panel UX — `project/ui/panels/booking.py`
- Wrap the agent call in a spinner and store the response status so a "needs_info"
  result reads correctly (not the generic "no alternatives"):
  ```python
  lang = lang_of(user)
  with st.spinner(t("panel.booking.searching", lang)):
      resp = booking_agent.process_agentic(ctx)
  st.session_state["pending_booking"] = {
      "status": resp.status,                       # NEW
      "message": resp.message,
      "alternatives": [a.model_dump() for a in resp.alternatives],
  }
  ```
- In `render`, when `pb["status"] == "needs_info"` show the message as an info box
  ("tell me a doctor or specialty…") instead of the no-alternatives warning.
- Add catalog key **`panel.booking.searching`** (en/si/ta), e.g.
  en "Finding available slots…", si "ලද හැකි වේලාවන් සොයමින්…",
  ta "கிடைக்கும் நேரங்களைத் தேடுகிறது…".

### Verify (Step 5)
- Delete `app.db`, restart; log in as `demo1`; sidebar **🔔 Check my reminders** →
  shows 1 due → **Send push** → `reminders.fire` returns 1, and an ntfy push lands
  at `https://ntfy.sh/medbridge-demo-<demo1_user_id>` (subscribe there first).
- Booking shows a spinner; "book me a heart doctor" returns real slots; with a key,
  logs show `INFO Booking via Pydantic AI agent`.
- `pytest` stays green.

---

## 5. Step 6 — Prescription OCR sample image + voice hardening

**Goal:** the prescription OCR flow demos without a live photo, and voice in/out
works in en/si/ta with graceful unavailability.

### 6a. Ship a sample prescription image — `project/kb/sample_prescriptions/`
- Create the folder and add a small image, e.g. `sample_rx_en.png`. Either drop in
  a real photo, or generate a typed one with Pillow (already transitively present
  via streamlit? if not, `pip install pillow`):
  ```python
  from PIL import Image, ImageDraw
  img = Image.new("RGB", (700, 360), "white"); d = ImageDraw.Draw(img)
  for i, line in enumerate([
      "City Clinic — Dr. A. Perera",
      "Patient: Nimal Perera",
      "Rx:",
      "  Paracetamol 500mg  — 1 tab three times daily",
      "  Amoxicillin 500mg  — 1 cap twice daily x5 days",
      "  Cetirizine 10mg    — 1 tab at night",
  ]): d.text((20, 30 + i*45), line, fill="black")
  img.save("project/kb/sample_prescriptions/sample_rx_en.png")
  ```
  Keep the drug names to ones the catalog stocks (see `project/kb/seed_medicines.json`)
  so the downstream pharmacy comparison returns results.
- In `project/ui/panels/prescription.py`, add a **"Use sample prescription"**
  selectbox/checkbox above the uploader. When chosen, read the sample file bytes
  and run the same `medicine_tracker.process_prescription(...)` path → confirm gate
  → pharmacy search. Keep the existing paste fallback. **Dosage stays verbatim** —
  do not change `vision_ocr` prompts.
- Add catalog keys for the new controls (en/si/ta), e.g. `panel.rx.use_sample`,
  `panel.rx.sample_label`.

### 6b. Voice hardening — `project/i18n/stt.py`, `tts.py`, `project/ui/panels/chat.py`
- These already fall back cleanly (STT returns `""` and shows
  `chat.voice_unavail` with no key; gTTS returns `None`). Hardening = verify +
  spinner: wrap the transcription call in `chat.py` with
  `st.spinner(t("chat.voice_transcribing", lang))` (add that key, en/si/ta).
- Manually confirm si/ta round-trip when keyed (record → transcribe → reply →
  TTS speaks). gTTS supports `si`/`ta` lang codes already.

### Verify (Step 6)
- Offline: prescription panel shows the unavailable warning but the **sample +
  paste** paths still reach the confirm gate and pharmacy table; no pharmacy lookup
  happens before the user confirms.
- Keyed: sample image → Gemini Vision transcribes → confirm → pharmacy comparison.
- Voice expander shows a spinner during transcription; en/si/ta all work keyed.

---

## 6. Step 7 — i18n completeness + JSON regex tightening + seed review

### 7a. Tighten the greedy `\{.*\}` regex
Three files each have `_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)` + a local
`_extract_json`: `project/agents/basic_chatbot.py`, `moderator.py`,
`specialist_panel.py`. The greedy regex grabs from the first `{` to the LAST `}`,
which breaks on any trailing prose containing braces. Replace each `_extract_json`
body with a **balanced-brace scanner** (recommended: put it once in a new
`project/agents/jsonutil.py` and import it in all three):

```python
import json

def extract_first_json(raw: str) -> dict | None:
    """Return the first *balanced* {...} object in an LLM response, else None.
    String-aware (ignores braces inside quoted strings) and nesting-aware."""
    start = raw.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = esc = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:            esc = False
            elif ch == "\\":   esc = True
            elif ch == '"':    in_str = False
            continue
        if ch == '"':   in_str = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(raw[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
```
Then delete the `_JSON_RE` constants and have each file call
`extract_first_json(...)`.

### 7b. i18n completeness
- Make sure every string added across Steps 5–6 exists in en/si/ta.
- Add a test (see Step 8) that asserts every `CATALOG` value has all three langs.
- Confirm `translate_dynamic` returns the input unchanged when no key is set.

### 7c. Demo seed review — `project/kb/seed_facilities.json`, `seed_pharmacy_prices.json`
- Every **specialty** must have ≥1 doctor with **available slots inside the next 7
  days**. Slots use `day_offset` from today (`seed.py::_resolve_date`). Audit the
  JSON: ensure each doctor has slots with small positive `day_offset` (1–6) and
  `is_available: true`, so booking always shows alternatives. Quick check:
  ```sql
  SELECT s.name, COUNT(*) FROM Specialty s
  JOIN Doctor d ON d.specialty_id=s.specialty_id
  JOIN AppointmentSlot a ON a.doctor_id=d.doctor_id
  WHERE a.is_available=1 AND a.date BETWEEN date('now') AND date('now','+7 day')
  GROUP BY s.name;
  ```
  (run via a tiny python `get_conn().execute(...)` against a freshly seeded db).
- Every demo medicine in `seed_medicines.json` should be stocked
  (`in_stock: true`) by at least one pharmacy in `seed_pharmacy_prices.json`.

### Verify (Step 7)
- `pytest` green (incl. the new i18n test).
- Each specialty returns alternatives; each demo medicine returns ≥1 pharmacy quote.

---

## 7. Step 8 — Tests across all four lanes

Add to `tests/` (fixtures already exist in `tests/conftest.py`: `seeded_db`,
`chroma_tmp`, `no_api_key`). Target one green `pytest` run, offline.

- **`tests/test_chatbot.py`** — heuristic routing: assert `bc.handle(1, "...")`
  classifies booking/medicine/report_review/general/emergency correctly with
  `no_api_key` (the LLM is never hit for unambiguous intents). Pattern used in the
  Step 2 verification.
- **`tests/test_emergency.py`** — `emergency.screen` true positives (chest pain,
  "can't breathe", suicide terms) and clean negatives (mild headache).
- **`tests/test_i18n.py`** — every `CATALOG` value has `en`/`si`/`ta`;
  `translate_dynamic("x","si")` returns `"x"` under `no_api_key`.
- **`tests/test_auth.py`** — `signup` hashes; `login` verifies; duplicate username
  rejected; wrong password → `None`.
- **`tests/test_reminders.py`** — `detect_reminder` regex (numeric/word/ISO/"next
  month"), `due_within` windowing, `fire` marks `notified=1` (mock ntfy or assert
  the NotificationLog row).
- **`tests/test_notifications.py`** — `ntfy_client.send` always writes a
  `NotificationLog` row even when the HTTP POST fails (point `NTFY_BASE` at an
  unreachable host / monkeypatch `requests.post` to raise → returns `False`, row
  still inserted).
- **Booking agent path** (`tests/test_booking.py`, extend): keep the offline
  fallback test; optionally assert `_get_booking_agent()` is non-`None` when a
  dummy key is set (build only — no network), proving the Step 3 fix stays fixed.

### Verify (Step 8): `python -m pytest -q` → all green, offline.

---

## 8. Step 9 — UI polish (theme + layout)

Keep Streamlit's structure; no fragile custom components.
- Refine **`.streamlit/config.toml`** (current starter is teal `#0d9488` on slate).
  Tune primary/background/secondaryBackground/text for a clean medical feel.
- Polish the branded banner (`project/ui/common.py::render_branding_styles` /
  `render_top_banner`) and the sidebar grouping.
- Put domain panels into tidy **cards/columns** with consistent spacing; add clear
  **empty/status states** (e.g., friendly placeholders before any flow runs).
- Ensure the new History expander and booking/medicine tables read cleanly on
  desktop width. Verify all polish strings remain localized (en/si/ta).

### Verify (Step 9): visual pass at `localhost:8501` in all three languages; nothing
overflows; `pytest` still green.

---

## 9. Step 10 — Final E2E + deploy verify

1. **Offline:** `python -m pytest -q` → green (CI-safe, no key).
2. **Local full-AI** (`project/.env` has the key): `streamlit run project/ui/app.py`
   and walk every flow:
   - "price of paracetamol" / "book a heart doctor" return in **<3s**, no hang.
   - Booking runs **through the Pydantic AI agent** (log line `Booking via Pydantic
     AI agent`); deterministic fallback when the key is unset.
   - Specialist panel → 3 distinct analyses + real agree/disagree.
   - Future-visit reminder → ntfy push in one click (seeded `demo1` reminder).
   - Prescription sample image → confirm gate → pharmacy comparison; dosage verbatim.
   - Voice in/out + every flow in **en/si/ta**; history timeline populates.
3. **Deploy** per [DEPLOY.md](DEPLOY.md): push branch → share.streamlit.io → main
   file `project/ui/app.py` → Python 3.12 → paste secrets TOML → deploy. Open the
   URL, log in as a `demo*` user, run each flow; confirm full-AI works and a
   rate-limited call degrades fast (heuristic) instead of hanging.

### Final checkpoint (Phase 3 done)
- `pytest` green; routing <3s; booking demonstrably via the Pydantic AI agent;
  every Interim-Report flow works in en/si/ta; reminder push fires; OCR+confirm and
  specialist panel work; hosted demo live on Streamlit Community Cloud.

---

## 10. Working conventions (keep doing what Steps 1–4 did)

- Branch `nisal`; **one commit per step** with a clear message; no PR/push to
  `main`/`Test` until asked.
- After each step: `python -m py_compile <changed files>` + `python -m pytest -q`
  + a quick functional check (seed a temp DB like the Step 4/5 verifications).
- New strings → add to `CATALOG` in en/si/ta immediately (don't leave raw keys).
- Respect lane ownership in [OWNERS.md](OWNERS.md)/[PLAN1.md](PLAN1.md) when it
  matters for review, but since one person is finishing Phase 3, the order above is
  the practical path.
