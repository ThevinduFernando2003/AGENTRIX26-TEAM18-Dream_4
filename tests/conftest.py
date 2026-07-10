"""Shared pytest fixtures for MedBridge AI.

Everything here runs **offline** — no API key required — so the suite is CI-safe:
- ``seeded_db``  : a throwaway SQLite seeded from the real loader, with
  ``db.get_conn()`` redirected to it for the duration of the test.
- ``chroma_tmp`` : a throwaway Chroma store built by the real ingest using the
  local ONNX embeddings (no key), with the retriever cache reset around it.
- ``no_api_key`` : guarantees the offline path (GEMINI_API_KEY removed).
"""

from __future__ import annotations

import pytest


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Redirect the app DB to a temp file and seed it. Yields the db module."""
    from project.db import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db._local.conn = None  # drop any cached connection bound to the real DB
    db.init_db(seed=True)
    yield db
    conn = getattr(db._local, "conn", None)
    if conn is not None:
        conn.close()
    db._local.conn = None


@pytest.fixture
def chroma_tmp(tmp_path, monkeypatch):
    """Build a throwaway Chroma index (local embeddings) and point retrieval at it."""
    from project.rag import embeddings, ingest, retriever

    monkeypatch.setattr(embeddings, "RAG_PERSIST_DIR", str(tmp_path / "chroma"))
    retriever.reset_cache()
    counts = ingest.ingest()
    yield counts
    retriever.reset_cache()


@pytest.fixture
def no_api_key(monkeypatch):
    """Force the offline / deterministic path regardless of LLM_PROVIDER."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
