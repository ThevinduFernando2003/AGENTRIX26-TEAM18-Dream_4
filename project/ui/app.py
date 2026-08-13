"""MedBridge AI — Streamlit entry point (thin shell).

Run with:
    streamlit run project/ui/app.py

This module only bootstraps the environment and orchestrates the panel modules in
``project/ui/panels/``. All UI lives in those panels (see the panel contract in
``project/ui/panels/__init__.py``); the chat router hands domain intents to each
panel via a ``route_request`` session signal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow `streamlit run project/ui/app.py` to find the `project` package.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(_ROOT / "project" / ".env")
load_dotenv(_ROOT / ".env")  # fallback


# --- Streamlit Community Cloud secrets bridge ------------------------------
# On Cloud there is no .env file; configuration is supplied via st.secrets.
# Every agent reads config from os.environ (e.g. os.environ.get("GEMINI_API_KEY")),
# so copy the relevant secrets across BEFORE importing any project module that
# reads the environment at import time. Local .env values already present in
# os.environ take precedence, so this is a no-op for local development.
_SECRET_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_STT_MODEL",
    "RAG_EMBED_BACKEND",
    "GEMINI_EMBED_MODEL",
    "NTFY_TOPIC_PREFIX",
    "NTFY_BASE",
    "CREWAI_TRACING_ENABLED",
    "OTEL_SDK_DISABLED",
)


def _bridge_secrets_to_env() -> None:
    try:
        secrets = st.secrets
    except Exception:
        return  # no secrets.toml configured (local dev) — nothing to bridge
    for key in _SECRET_KEYS:
        if key in os.environ:
            continue
        try:
            val = secrets[key]
        except Exception:
            continue
        if val is not None:
            os.environ[key] = str(val)


_bridge_secrets_to_env()

from project.db.db import init_db  # noqa: E402
from project.ui import common  # noqa: E402
from project.ui.auth import render_auth_gate  # noqa: E402
from project.ui.panels import (  # noqa: E402
    appointments,
    booking,
    chat,
    emergency,
    history,
    medicine,
    prescription,
    report,
    sidebar,
)


st.set_page_config(page_title="MedBridge AI", page_icon="🩺", layout="wide")

# Lazy DB init on first run.
if not st.session_state.get("_db_inited"):
    init_db(seed=True)
    st.session_state["_db_inited"] = True

# Lazy RAG index build on first run — idempotent, local embeddings, no key needed.
# Ensures RAG grounding works on a fresh clone without a manual ingest step.
if not st.session_state.get("_rag_inited"):
    from project.rag.ingest import ensure_ingested  # noqa: E402

    ensure_ingested()
    st.session_state["_rag_inited"] = True


def main() -> None:
    common.render_branding_styles()

    user = render_auth_gate()
    if not user:
        return

    sidebar.render(user)

    lang = common.lang_of(user)
    common.render_top_banner(lang)

    # Active in-progress panels render above chat so they're not buried.
    emergency.render(user)
    booking.render(user)
    medicine.render(user)
    report.render(user)
    prescription.render(user)

    # Confirmed appointments + cancel (Phase 0 / FR-P08).
    appointments.render(user)

    # Read-only cross-domain activity timeline (collapsed by default).
    history.render(user)

    # Chat history + voice input + intent router.
    chat.render(user)

    # Footer disclaimer always visible.
    st.markdown("---")
    st.markdown(common.disclaimer(lang))


if __name__ == "__main__":
    main()
else:
    # Streamlit imports this as a module on each rerun.
    main()
