"""Medicine smoke tests — exact/RAG matching, precision guard, haversine (offline)."""

from __future__ import annotations

from project.agents.medicine_tracker import haversine_km, match_medicines


def test_match_exact_catalog_name(seeded_db, no_api_key):
    _ids, names, unmatched = match_medicines(["Paracetamol 500mg"])
    assert "Paracetamol 500mg" in names
    assert unmatched == []


def test_match_resolves_misspelling_via_rag(seeded_db, chroma_tmp, no_api_key):
    _ids, names, _unmatched = match_medicines(["parasetmol"])
    assert names == ["Paracetamol 500mg"]


def test_match_rejects_nonsense(seeded_db, chroma_tmp, no_api_key):
    _ids, names, unmatched = match_medicines(["xyz nonsense drug"])
    assert names == []
    assert "xyz nonsense drug" in unmatched


def test_haversine_zero_distance():
    assert haversine_km(6.9271, 79.8612, 6.9271, 79.8612) < 0.001
