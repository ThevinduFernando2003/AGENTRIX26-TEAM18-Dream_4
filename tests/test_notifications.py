"""ntfy client — a NotificationLog row is always written, even when the POST fails.

The audit trail must not depend on the network: whether ntfy returns 2xx, a non-2xx,
or raises, send() logs the attempt and never raises to the caller.
"""

from __future__ import annotations

from project.notifications import ntfy_client


def _log_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM NotificationLog").fetchone()["n"]


class _FakeResp:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.text = "fake"


def test_logs_when_post_raises(seeded_db, monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(ntfy_client.requests, "post", _raise)
    conn = seeded_db.get_conn()
    before = _log_count(conn)

    ok = ntfy_client.send("topic-x", "Title", "Body", user_id=1, notif_type="test")
    assert ok is False                       # POST failed
    assert _log_count(conn) == before + 1    # row still written


def test_logs_on_non_2xx(seeded_db, monkeypatch):
    monkeypatch.setattr(ntfy_client.requests, "post", lambda *a, **k: _FakeResp(500))
    conn = seeded_db.get_conn()
    before = _log_count(conn)

    ok = ntfy_client.send("topic-x", "Title", "Body", user_id=1, notif_type="test")
    assert ok is False
    assert _log_count(conn) == before + 1


def test_returns_true_and_logs_on_success(seeded_db, monkeypatch):
    monkeypatch.setattr(ntfy_client.requests, "post", lambda *a, **k: _FakeResp(200))
    conn = seeded_db.get_conn()
    before = _log_count(conn)

    ok = ntfy_client.send("topic-x", "Title", "Body", user_id=1, notif_type="test")
    assert ok is True
    assert _log_count(conn) == before + 1


def test_topic_for_user_uses_prefix():
    assert ntfy_client.topic_for_user(7).endswith("-7")
