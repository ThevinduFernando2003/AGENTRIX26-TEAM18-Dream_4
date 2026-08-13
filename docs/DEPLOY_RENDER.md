# Deploy MedBridge on Render (recommended for Phase 1)

Streamlit is a **single web process** (UI + domain logic). Deploy that process on Render.  
Do **not** expect Vercel to host Streamlit; Vercel is for static/Next.js (Phase 2).

---

## Prerequisites

- GitHub repo with branch `booking` pushed to your `origin`
- Render account
- API key (`GEMINI_API_KEY` or `OPENAI_API_KEY`)

---

## Step-by-step

### 1. Add Postgres (strongly recommended)

1. Render → **New → PostgreSQL**
2. Create instance; copy **External Database URL** (or Internal if same region)
3. You will set this as `DATABASE_URL` on the web service

SQLite on Render’s ephemeral disk loses data on restart — avoid for demos that must persist.

### 2. Create Web Service (patient app)

1. Render → **New → Web Service** → connect GitHub repo  
2. **Branch:** `booking`  
3. **Runtime:** Python 3  
4. **Build command:**

```bash
pip install -r requirements-dev.txt
```

5. **Start command:**

```bash
streamlit run project/ui/app.py --server.port=$PORT --server.address=0.0.0.0 --browser.gatherUsageStats=false
```

6. **Environment variables:**

| Key | Example / notes |
|---|---|
| `DATABASE_URL` | Postgres URL from step 1 |
| `LLM_PROVIDER` | `gemini` or `openai` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | Your key |
| `RAG_EMBED_BACKEND` | `local` |
| `NTFY_TOPIC_PREFIX` | `medbridge-render` |
| `SMS_PROVIDER` | `stub` (or `http` + `SMS_HTTP_URL`) |
| `PYTHON_VERSION` | `3.11.9` (optional pin) |

7. Deploy → open the public URL → login `demo1` / `demo1pass` after first seed.

### 3. Optional second service (supplier portal)

Same repo/branch/build; **start command:**

```bash
streamlit run project/ui/supplier_portal.py --server.port=$PORT --server.address=0.0.0.0 --browser.gatherUsageStats=false
```

Use the **same** `DATABASE_URL` so patient and supplier share data.  
Staff logins: `union` / `unionpass`, `nawaloka` / `nawalokapass`.

### 4. Optional reminder worker

Render → **Background Worker** (or cron job):

```bash
python -m project.workers.reminder_worker
```

Same `DATABASE_URL` + ntfy/SMS env as the web service.

### 5. Smoke test after deploy

1. Consent signup or demo login  
2. Book → cancel / reschedule  
3. Medicine search shows freshness  
4. Supplier CSV or Losartan stock toggle → patient refresh  
5. Emergency confirm → ntfy (and SMS stub log)  
6. `pytest` stays green on GitHub Actions (CI is source of truth for regressions)

---

## Why not Vercel + Render backend today?

| Layer | Today | Vercel-ready? |
|---|---|---|
| Patient UI | Streamlit | No |
| Supplier UI | Streamlit | No |
| API | Embedded in Streamlit | No separate API |
| Target Phase 2 | FastAPI + React/PWA | Yes — Vercel UI + Render API |

---

## Streamlit Community Cloud (alternative)

1. share.streamlit.io → New app → `project/ui/app.py`  
2. Secrets mirror `project/.env.example`  
3. SQLite on Cloud is fragile; prefer external Postgres + `DATABASE_URL` when possible  

`project/ui/app.py` already bridges `st.secrets` → `os.environ`.
