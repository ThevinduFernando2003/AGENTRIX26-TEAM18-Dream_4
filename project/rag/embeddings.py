"""Embedding-function factory shared by RAG ingest and retrieval.

One factory so the vectors written at ingest time and the vectors used at query
time always come from the *same* model — mixing models silently destroys recall.

Strategy (default LOCAL so the index is independent of the chat/OCR API key):
- Default                       -> ChromaDB's bundled local model (ONNX MiniLM via
  ``onnxruntime``). Real vector search, no network, no key, no quota. This is the
  "Local RAG" the proposal describes, and it keeps the persisted index consistent
  whether or not ``GEMINI_API_KEY`` is set — so swapping in a paid key never
  requires a re-ingest and never causes a dimension mismatch.
- ``RAG_EMBED_BACKEND=gemini``  -> Gemini ``gemini-embedding-001`` (opt-in only;
  requires a re-ingest because the vector dimension differs from the local model).

Gemini embeddings are validated with a live health-check at factory time, so a
missing/renamed model or an exhausted quota degrades cleanly back to the local
model instead of silently returning empty results at query time.

Both return a ChromaDB ``EmbeddingFunction`` so callers just pass the result to
``client.get_or_create_collection(..., embedding_function=...)``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from chromadb import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger("medbridge.rag.embeddings")

# Persisted Chroma store. Gitignored. Overridable so tests/CI point at a tmp dir.
_DEFAULT_PERSIST = Path(__file__).resolve().parent / "chroma_store"
RAG_PERSIST_DIR = os.environ.get("RAG_PERSIST_DIR", str(_DEFAULT_PERSIST))

# gemini-embedding-001 is the current Generative Language API embedding model.
# (text-embedding-004 has been retired and 404s on the v1beta catalog.)
_GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")


class _GeminiEmbeddingFunction(EmbeddingFunction[Documents]):
    """Wraps Gemini ``gemini-embedding-001`` as a ChromaDB embedding function."""

    def __init__(self, api_key: str, model: str = _GEMINI_EMBED_MODEL) -> None:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=api_key)
        self._genai = genai
        self._model = model

    def __call__(self, input: Documents) -> Embeddings:
        out: list[list[float]] = []
        for text in input:
            resp = self._genai.embed_content(model=self._model, content=text)
            # embed_content returns {"embedding": [...]} (single) — be defensive.
            emb = resp["embedding"] if isinstance(resp, dict) else resp.embedding
            out.append(list(emb))
        return out


def _gemini_requested() -> bool:
    """Gemini embeddings are opt-in (``RAG_EMBED_BACKEND=gemini``) AND need a key.

    Default is local ONNX so the index never depends on the chat/OCR key.
    """
    return (
        os.environ.get("RAG_EMBED_BACKEND", "local").lower() == "gemini"
        and bool(os.environ.get("GEMINI_API_KEY"))
    )


def get_embedding_function() -> EmbeddingFunction:
    """Return the active embedding function: local ONNX by default, Gemini if opted in.

    Never raises: if the Gemini path can't initialise OR fails a live health-check
    (renamed model, exhausted quota, offline), fall back to the local model so RAG
    keeps working and the persisted index stays consistent.
    """
    if _gemini_requested():
        try:
            fn = _GeminiEmbeddingFunction(api_key=os.environ["GEMINI_API_KEY"])
            fn(["health-check"])  # validate at call time, not just configure time
            logger.info("RAG embeddings: using Gemini %s", _GEMINI_EMBED_MODEL)
            return fn
        except Exception as exc:
            logger.warning("Gemini embeddings unavailable (%s) — using local model", exc)
    from chromadb.utils import embedding_functions

    return embedding_functions.DefaultEmbeddingFunction()


def using_gemini() -> bool:
    """True when the Gemini embedding path is requested (for logging/diagnostics)."""
    return _gemini_requested()
