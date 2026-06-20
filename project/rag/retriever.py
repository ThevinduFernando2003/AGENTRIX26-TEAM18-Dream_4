"""Vector retrieval — the contract every Phase-2 caller depends on.

Backed by the persistent Chroma index built by :mod:`project.rag.ingest`, embedded
with :func:`project.rag.embeddings.get_embedding_function` (local ONNX offline,
Gemini ``text-embedding-004`` when keyed). The offline / not-yet-ingested path
returns ``[]`` cleanly and NEVER raises, so callers can always fall back to their
deterministic heuristics.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("medbridge.rag.retriever")

# Cache the client + per-name collections across calls (Streamlit reruns a lot).
_client = None
_collections: dict = {}


def _get_collection(name: str):
    global _client
    from .embeddings import RAG_PERSIST_DIR, get_embedding_function

    if name in _collections:
        return _collections[name]
    import chromadb

    if _client is None:
        _client = chromadb.PersistentClient(path=RAG_PERSIST_DIR)
    # get_collection raises if it doesn't exist yet (not ingested) — caller handles [].
    collection = _client.get_collection(name=name, embedding_function=get_embedding_function())
    _collections[name] = collection
    return collection


def reset_cache() -> None:
    """Drop cached client/collections. Used by tests that swap RAG_PERSIST_DIR."""
    global _client
    _client = None
    _collections.clear()


def retrieve(query: str, collection: str, k: int = 5) -> list[dict]:
    """Return up to ``k`` knowledge-base chunks most relevant to ``query``.

    Contract (stable across phases):
        - ``list[dict]`` of length 0..k, each exactly
          ``{"text": str, "metadata": dict, "score": float}``, ordered by
          descending ``score`` (cosine similarity in [0, 1], higher == closer).
        - ``collection`` selects the index: "symptoms" | "facilities" | "medicines".
        - The offline / no-index / error path returns ``[]`` and NEVER raises.
    """
    query = (query or "").strip()
    if not query:
        return []
    try:
        coll = _get_collection(collection)
        res = coll.query(query_texts=[query], n_results=k)
    except Exception as exc:
        logger.debug("retrieve(%r, %r) → [] (%s)", query, collection, exc)
        return []

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    out: list[dict] = []
    for i, text in enumerate(docs):
        dist = dists[i] if i < len(dists) else 1.0
        out.append(
            {
                "text": text,
                "metadata": metas[i] if i < len(metas) else {},
                "score": max(0.0, 1.0 - float(dist)),
            }
        )
    out.sort(key=lambda d: d["score"], reverse=True)
    return out
