"""RAG smoke tests — retrieval grounding, safety, and ingest idempotency (offline)."""

from __future__ import annotations

from project.rag import retrieve


def test_retrieve_grounds_specialty(chroma_tmp, no_api_key):
    hits = retrieve("crushing chest pain and breathlessness", "symptoms", 3)
    assert hits, "expected at least one symptom hit"
    assert hits[0]["metadata"]["specialty"] == "Cardiology"
    assert 0.0 <= hits[0]["score"] <= 1.0
    # ordered by descending score
    assert all(hits[i]["score"] >= hits[i + 1]["score"] for i in range(len(hits) - 1))


def test_retrieve_missing_collection_is_safe(chroma_tmp, no_api_key):
    assert retrieve("anything", "does_not_exist", 3) == []


def test_retrieve_empty_query_is_safe(chroma_tmp, no_api_key):
    assert retrieve("", "symptoms", 3) == []


def test_ingest_is_idempotent(chroma_tmp, no_api_key):
    from project.rag import ingest

    first = chroma_tmp  # counts from the fixture's initial ingest
    second = ingest.ingest()
    assert first == second  # same chunk counts → upsert, no duplicates
