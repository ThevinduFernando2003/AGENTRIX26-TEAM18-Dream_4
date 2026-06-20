# Deploying MedBridge AI to Streamlit Community Cloud

The live demo runs on **Streamlit Community Cloud** (free, deploys straight from
GitHub, built-in secrets). It runs in **full-AI mode** — a Gemini key is supplied
as a Cloud secret, so live routing, the Pydantic AI booking agent, the specialist
panel, translation and OCR/voice are all active. Every feature still degrades
gracefully if the key is removed or rate-limited.

## One-time setup

1. Push this repo to GitHub (the branch you want to deploy — e.g. `main`).
2. Go to <https://share.streamlit.io> → **Create app** → **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `Agentrix-ComES/AGENTRIX26-TEAM18-Dream_4`
   - **Branch:** `main` (or your demo branch)
   - **Main file path:** `project/ui/app.py`
   - **Advanced settings → Python version:** `3.12`
4. **Advanced settings → Secrets:** paste the TOML below (this is the Cloud
   equivalent of `project/.env`). The app's secrets bridge in
   [`app.py`](project/ui/app.py) copies these into `os.environ` at startup.

   ```toml
   GEMINI_API_KEY = "your-rotated-billed-key"
   GEMINI_MODEL = "gemini-2.5-flash"
   RAG_EMBED_BACKEND = "local"
   NTFY_TOPIC_PREFIX = "medbridge-demo"
   CREWAI_TRACING_ENABLED = "false"
   OTEL_SDK_DISABLED = "true"
   ```

5. Click **Deploy**. First boot seeds the SQLite DB and builds the local Chroma
   RAG index automatically (downloads the MiniLM ONNX model once → the very first
   cold start is slower, then fast). No manual ingest step is needed.

## Dependencies

Streamlit Cloud installs from the **repo-root [`requirements.txt`](requirements.txt)**
(pinned to verified versions). `project/requirements.txt` is the looser local-dev
manifest and is not used by Cloud.

## Secret hygiene

- `project/.env` is gitignored — the live key lives **only** in the Cloud Secrets
  UI, never in the repo.
- `.streamlit/secrets.toml` is gitignored too; only `.streamlit/config.toml`
  (the theme) is committed.
- ⚠️ A Gemini key was committed earlier in git history — make sure that key is
  **rotated/disabled** in Google AI Studio before going public, and use the new
  key for the secret above.

## Offline / no-key mode

Remove `GEMINI_API_KEY` from secrets to run the demo fully offline: RAG still
works (local ONNX embeddings), and routing, specialists, translation and OCR/voice
fall back to deterministic/stub paths. Useful as a zero-cost, rate-limit-proof
fallback during judging.

## Notes & limits

- Community Cloud apps sleep after inactivity and cold-start on the next visit —
  open the URL a minute before the demo.
- The filesystem is ephemeral; the DB + RAG index rebuild on each cold start
  (seed + auto-ingest), which is by design.
- The install is heavy (crewai + chromadb + onnxruntime). If a build hits the
  resource limit, the offline mode above needs none of the LLM stack at runtime.
