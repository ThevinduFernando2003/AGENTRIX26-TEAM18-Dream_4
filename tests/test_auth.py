"""Auth — bcrypt hashing, login verification, duplicate + weak-password rejection."""

from __future__ import annotations

from project.ui import auth


def test_signup_hashes_and_login_verifies(seeded_db):
    ok, _ = auth.signup("alice_t", "secret123", consent_accepted=True)
    assert ok

    row = seeded_db.get_conn().execute(
        "SELECT password_hash FROM User WHERE username = ?", ("alice_t",)
    ).fetchone()
    assert row["password_hash"] != "secret123"      # never stored in plaintext
    assert row["password_hash"].startswith("$2")    # bcrypt hash marker

    uid = auth.login("alice_t", "secret123")
    assert isinstance(uid, int)


def test_login_wrong_password_and_unknown_user_return_none(seeded_db):
    auth.signup("bob_t", "secret123", consent_accepted=True)
    assert auth.login("bob_t", "wrong-password") is None
    assert auth.login("does_not_exist", "secret123") is None


def test_duplicate_username_rejected(seeded_db):
    ok1, _ = auth.signup("carol_t", "secret123", consent_accepted=True)
    ok2, _ = auth.signup("carol_t", "secret123", consent_accepted=True)
    assert ok1 is True
    assert ok2 is False


def test_weak_password_rejected(seeded_db):
    ok, msg = auth.signup("dave_t", "123", consent_accepted=True)
    assert ok is False
    assert "6" in msg


def test_signup_requires_consent(seeded_db):
    ok, msg = auth.signup("erin_t", "secret123", consent_accepted=False)
    assert ok is False
    assert "consent" in msg.lower()


def test_signup_with_consent_stores_timestamp(seeded_db):
    ok, _ = auth.signup("frank_t", "secret123", consent_accepted=True)
    assert ok is True
    row = seeded_db.get_conn().execute(
        "SELECT consent_accepted_at FROM User WHERE username = ?", ("frank_t",)
    ).fetchone()
    assert row["consent_accepted_at"]
    assert "T" in row["consent_accepted_at"] or "-" in row["consent_accepted_at"]
