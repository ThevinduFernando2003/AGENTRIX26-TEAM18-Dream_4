"""Embedding-function factory shared by RAG ingest and retrieval.

One factory so the vectors written at ingest time and the vectors used at query
time always come from the *same* model — mixing models silently destroys recall.

Strategy (per the free-tier + offline constraint):
- ``GEMINI_API_KEY`` set  -> Gemini ``text-embedding-004`` (free tier).
- no key / offline / CI   -> ChromaDB's bundled local model (ONNX MiniLM via
  ``onnxruntime``). Real vector search, no network, no key.

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

_GEMINI_EMBED_MODEL = "models/text-embedding-004"


class _GeminiEmbeddingFunction(EmbeddingFunction[Documents]):
    """Wraps Gemini ``text-embedding-004`` as a ChromaDB embedding function."""

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


def get_embedding_function() -> EmbeddingFunction:
    """Return the active embedding function: Gemini if keyed, else local ONNX.

    Never raises: if the Gemini path can't initialise, fall back to local so RAG
    keeps working.
    """
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            return _GeminiEmbeddingFunction(api_key=key)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Gemini embeddings unavailable, using local model: %s", exc)
    from chromadb.utils import embedding_functions

    return embedding_functions.DefaultEmbeddingFunction()


def using_gemini() -> bool:
    """True when the Gemini embedding path is active (for logging/diagnostics)."""
    return bool(os.environ.get("GEMINI_API_KEY"))
