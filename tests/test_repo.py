"""Repository seam smoke tests."""

from __future__ import annotations

from project.db import repo


def test_repo_fetch_and_transaction(seeded_db):
    row = repo.fetchone("SELECT COUNT(*) AS n FROM User")
    assert row["n"] >= 1

    with repo.transaction() as conn:
        before = conn.execute("SELECT COUNT(*) AS n FROM Medicine").fetchone()["n"]
        assert before >= 1

    rows = repo.fetchall("SELECT medicine_id FROM Medicine LIMIT 3")
    assert len(rows) <= 3
