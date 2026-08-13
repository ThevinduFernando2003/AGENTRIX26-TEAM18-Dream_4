"""Medicine smoke tests — exact/RAG matching, precision guard, haversine (offline)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from project.agents.medicine_tracker import freshness_label, haversine_km, match_medicines, quotes_for


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


def test_freshness_label_none_is_seed():
    assert freshness_label(None) == "SEED"
    assert freshness_label("") == "SEED"


def test_freshness_label_hours_and_days():
    now = datetime.now(timezone.utc)
    assert freshness_label((now - timedelta(minutes=20)).isoformat()) == "Updated <1h ago"
    assert freshness_label((now - timedelta(hours=5)).isoformat()).startswith("Updated 5h")
    assert freshness_label((now - timedelta(days=3)).isoformat()).startswith("Updated 3d")


def test_quotes_include_freshness(seeded_db, no_api_key):
    ids, _names, unmatched = match_medicines(["Paracetamol 500mg"])
    assert unmatched == []
    quotes = quotes_for(ids)
    assert quotes
    assert all(q.freshness_label for q in quotes)
