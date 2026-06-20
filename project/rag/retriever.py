"""Vector retrieval interface — the contract every Phase-2 caller depends on.

In Phase 1 this is a deterministic stub that always returns an empty list, so the
chatbot, booking agent, and medicine tracker can be wired against the real call
signature now and have it light up in Phase 2 without any import churn.
"""

from __future__ import annotations


def retrieve(query: str, collection: str, k: int = 5) -> list[dict]:
    """Return up to ``k`` knowledge-base chunks most relevant to ``query``.

    Phase-1 behaviour: returns ``[]`` (no index yet). Phase 2 backs this with a
    persistent Chroma collection embedded via Gemini ``text-embedding-004``.

    Contract — what callers may rely on across phases:
        - Returns a ``list[dict]`` of length 0..k. Each dict has exactly:
              {
                  "text": str,        # the chunk content
                  "metadata": dict,   # provenance, e.g. {"source": "...", "specialty": "..."}
                  "score": float,     # similarity in [0, 1]; higher == closer
              }
          ordered by descending ``score``.
        - ``collection`` selects which index to search, e.g. "symptoms",
          "facilities", "medicines".
        - The offline / no-API-key path returns ``[]`` cleanly and NEVER raises.

    Args:
        query: Free-text query (a symptom description, drug name, etc.).
        collection: Name of the knowledge collection to search.
        k: Maximum number of results to return.
    """
    return []
