"""RAG subsystem for MedBridge AI.

Phase 1 ships only the public interface (a stubbed `retrieve`). Phase 2 backs it
with a persistent Chroma index + Gemini `text-embedding-004` (free tier), plus a
deterministic offline fallback. Callers should import from here:

    from project.rag import retrieve
"""

from __future__ import annotations

from .retriever import retrieve

__all__ = ["retrieve"]
