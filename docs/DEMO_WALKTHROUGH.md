# MedBridge AI — Full Demo Walkthrough (Step by Step)

**Goal:** Get a Gemini (or OpenAI) API key, wire it into the app, boot patient + supplier apps, and run the full viva demo.

**Time:** ~20–30 min first setup · ~12 min live demo after that.

---

## 0. What you need

| Item | Notes |
|---|---|
| Python 3.11+ | This machine has 3.13 — OK if install succeeds |
| Internet | For pip + LLM + ntfy |
| Google account | For a **free** Gemini API key (recommended) |
| Phone (optional) | To receive ntfy family alerts during demo |

> I cannot create a Google/OpenAI API key for you. You create it in their console (2 minutes), then paste it into `project/.env`.

---

## 1. Create a Gemini API key (recommended)

1. Open **[Google AI Studio](https://aistudio.google.com/apikey)** and sign in with Google.
2. Click **Create API key**.
3. Choose/create a Google Cloud project if prompted → **Create**.
4. **Copy** the key (starts with `AIza...`). Keep it private — never commit it.

### Optional: OpenAI instead

1. Open **[OpenAI API keys](https://platform.openai.com/api-keys)**.
2. Create a key → copy it (`sk-...`).
3. In `.env` set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...` (see §2).

---

## 2. Connect the API key (required for full LLM demo)

The file `project/.env` already exists. **You must paste your real key** — nothing else will unlock chat/OCR/panel LLM features.

**Path:** `d:\Dev\Competitions\Agentrix\MedBridge-AI\project\.env`

Open it:

```powershell
notepad d:\Dev\Competitions\Agentrix\MedBridge-AI\project\.env
```

Find this line:

```env
GEMINI_API_KEY=PASTE_YOUR_GEMINI_API_KEY_HERE
```

Replace with your key from AI Studio (example shape only):

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy................................
GEMINI_MODEL=gemini-2.5-flash
RAG_EMBED_BACKEND=local
NTFY_TOPIC_PREFIX=medbridge-demo
CREWAI_TRACING_ENABLED=false
OTEL_SDK_DISABLED=true
```

Rules: **no quotes**, **no spaces** around `=`, save the file, then **restart Streamlit** if it was already running.

### OpenAI (alternative)

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-................................
OPENAI_MODEL=gpt-4o-mini
OPENAI_STT_MODEL=whisper-1
RAG_EMBED_BACKEND=local
NTFY_TOPIC_PREFIX=medbridge-demo
CREWAI_TRACING_ENABLED=false
OTEL_SDK_DISABLED=true
```

**How the app loads it:** `project/ui/app.py` calls `load_dotenv(.../project/.env)` on startup. Agents read `os.environ` via `project/llm.py`.

**Sanity check after paste:**

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
# Should print True and hide the key
project\venv\Scripts\python -c "from dotenv import load_dotenv; import os; load_dotenv('project/.env'); k=os.getenv('GEMINI_API_KEY',''); print('key_set=', bool(k and not k.startswith('PASTE')), 'len=', len(k))"
```

---

## 3. One-time install (venv + deps + DB)

> **Status on this machine:** venv is already created, packages installed, and DB seeded (`demo1`–`demo6`). Skip to §2 (paste key) then §4 (run) unless you need a clean reinstall.

Open **PowerShell** in the repo root:

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI

# 1) Virtual environment
python -m venv project\venv
project\venv\Scripts\Activate.ps1

# If activation is blocked once:
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 2) Install packages (5–15 min first time)
pip install -U pip
pip install -r project\requirements.txt
pip install -r requirements-dev.txt

# Extra RAG deps used by the app (if not already pulled in):
pip install chromadb onnxruntime sentence-transformers 2>$null

# 3) Create SQLite DB + seed demo users/doctors/pharmacies
python -m project.db.db

# 4) Optional: build RAG index now (also auto-builds on first app run)
python -m project.rag.ingest
```

**Demo logins after seed:**

| Username | Password | Language |
|---|---|---|
| `demo1` | `demo1pass` | English |
| `demo3` | `demo3pass` | Sinhala |
| `demo4` | `demo4pass` | Tamil |

---

## 4. Start the apps

### Terminal A — Patient app (main demo)

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1
streamlit run project\ui\app.py
```

→ Browser: **http://localhost:8501**

### Terminal B — Supplier portal (viva-prep addon)

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1
streamlit run project\ui\supplier_portal.py --server.port 8502
```

→ Browser: **http://localhost:8502**

### Phone — family alerts (optional but impressive)

1. After login as `demo1`, open the **sidebar**.
2. Copy the ntfy topic URL (looks like `https://ntfy.sh/medbridge-demo-<user_id>`).
3. On your phone browser, open that URL → **Subscribe**, or install the [ntfy app](https://ntfy.sh/) and subscribe to the topic name.

---

## 5. First-run UI checklist (2 min)

1. Open **http://localhost:8501**
2. Login: `demo1` / `demo1pass`
3. Sidebar → set **city / location** to Colombo (or allow geolocation)
4. Confirm language = English
5. Send a quick test: `hello` — you should get a warm reply (proves the API key works)
6. If reply is a short heuristic stub and logs show no LLM: **key missing or wrong** → re-check §2

---

## 6. Full demo script (step by step — ~12 min)

Do these **in order**. Keep supplier portal tab ready for step 4.

### Step 1 — Emergency (regex before LLM)

**Type in chat:**

```text
I have severe chest pain and can't breathe
```

**Expect:**
- Red emergency panel
- Matched terms shown
- Click **Confirm**
- `tel:1990` (Suwa Seriya) link
- Phone buzz if ntfy subscribed

**Say:** “Emergency screening is pure regex and runs *before* any LLM.”

---

### Step 2 — Booking conflict → alternatives → book

**Type:**

```text
Book me with Dr. Sunil Perera tomorrow at 10:00
```

**Expect:**
- Requested slot full / conflict
- 3–5 alternative slots
- Click **Book** on one
- Green **success card** (doctor, date, fee)
- ntfy booking confirmation

**Say:** “Pydantic AI proposes via typed SQL tools; only deterministic `book()` writes atomically.”

---

### Step 3 — Medicine price comparison

**Type:**

```text
I need prices for Panadol and Amoxicillin
```

**Expect:**
- Table of pharmacies
- LKR totals, distance, “Has all?” / stock badges
- Complete baskets ranked first

**Say:** “Fuzzy + RAG matching; sorted by complete basket, then cost, then distance.”

---

### Step 4 — Supplier portal (two-sided platform)

1. Open **http://localhost:8502**
2. Pharmacy tab → select **Union Chemists**
3. Find **Losartan** → toggle **in stock** → save/publish
4. Back to patient app → type:

```text
price of Losartan
```

**Expect:** Union Chemists now appears (or shows in-stock) — live DB write.

**Say:** “Suppliers publish INTO MedBridge; we fetch nothing. Platform is the source of truth.”

---

### Step 5 — Specialist panel + moderator

1. Trigger report review (chat or report panel), e.g.:

```text
Can you review my medical report?
```

2. Pick sample: `project/kb/sample_reports/report_ambiguous_findings.txt`
3. Run the **3-specialist panel**

**Expect:**
- Three independent opinions (cardiology / internal / radiology)
- Moderator consensus
- Non-empty **points of disagreement**
- Optional ntfy “report complete”

**Say:** “Three threads, no shared state; disagreement list never empty by code.”

---

### Step 6 — Prescription OCR + confirm gate

1. Open prescription panel / flow
2. Upload: `project/kb/sample_prescriptions/sample_rx_en.png`  
   *(or paste text from `sample_rx_en.txt` if OCR is slow)*
3. **Step 1** upload → **Step 2** edit/confirm text → **Step 3** pharmacy compare

**Expect:** No pharmacy lookup until you confirm.

**Say:** “Human-in-the-loop; dosage only from catalog text.”

---

### Step 7 — Sinhala + reminder

1. Logout → login `demo3` / `demo3pass`
2. Send one short message (UI in Sinhala)
3. Type (English is fine for detector):

```text
come back in 2 weeks
```

4. Sidebar → **Reminders** → fire / show due → ntfy push

**Say:** “Trilingual + voice; reminders are regex, idempotent.”

---

### Step 8 — Close

Optional proof: temporarily rename/clear `GEMINI_API_KEY` and show heuristics still answer — then restore the key.

**Closing line:** “Turn the key off and the demo still runs on deterministic fallbacks. Structural safety.”

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Heuristic-only replies / no OCR | Key not loaded — check `.env` path, no quotes, restart Streamlit |
| `GEMINI_API_KEY=PASTE_...` still there | You forgot to replace the placeholder |
| 429 / quota errors | Wait, or switch `LLM_PROVIDER=openai`, or use a billed Gemini key |
| Import / CrewAI errors on Python 3.13 | Prefer Python 3.11–3.12 if install fails |
| Port in use | `streamlit run ... --server.port 8503` |
| Empty medicine/booking data | Re-run `python -m project.db.db` |
| RAG empty | `python -m project.rag.ingest` or just use the app once (auto-ingest) |
| ntfy silent | Open topic URL on phone; check sidebar topic matches |
| Activation policy error | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

### Restart clean (demo day)

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1
Remove-Item project\db\app.db -ErrorAction SilentlyContinue
# also delete chroma persist folder if present under project/rag or project/
python -m project.db.db
streamlit run project\ui\app.py
```

---

## 8. Quick command cheat sheet

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1

# Edit key
notepad project\.env

# Patient
streamlit run project\ui\app.py

# Supplier
streamlit run project\ui\supplier_portal.py --server.port 8502

# Tests (offline)
pytest -q
```

---

## 9. Security reminder

- `project/.env` is **gitignored** — never commit a real key
- If a key leaks in chat/screenshot → **rotate it** in AI Studio / OpenAI dashboard
- Free Gemini tier has daily limits — rehearse with OpenAI or spare the quota for viva day

---

**Next:** Paste your Gemini key into `project/.env`, run §3–§4, then walk §6 once before the viva.
