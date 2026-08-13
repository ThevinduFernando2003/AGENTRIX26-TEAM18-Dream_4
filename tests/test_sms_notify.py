"""Emergency SMS adapter + notify orchestration (offline)."""

from __future__ import annotations

from project.notifications import notify, sms_client


def test_sms_stub_logs_and_succeeds(seeded_db, monkeypatch):
    monkeypatch.setenv("SMS_PROVIDER", "stub")
    monkeypatch.setenv("SMS_STUB_OK", "1")
    assert sms_client.send_sms("0771234567", "test alert", user_id=1) is True
    row = seeded_db.get_conn().execute(
        """SELECT channel, type FROM NotificationLog
           WHERE user_id = 1 AND type = 'emergency_sms'
           ORDER BY id DESC LIMIT 1"""
    ).fetchone()
    assert row["channel"] == "sms:stub"


def test_sms_stub_can_fail(seeded_db, monkeypatch):
    monkeypatch.setenv("SMS_PROVIDER", "stub")
    monkeypatch.setenv("SMS_STUB_OK", "0")
    assert sms_client.send_sms("0771234567", "test", user_id=1) is False


def test_notify_emergency_calls_ntfy_and_sms(seeded_db, monkeypatch):
    monkeypatch.setenv("SMS_PROVIDER", "stub")
    monkeypatch.setenv("SMS_STUB_OK", "1")
    monkeypatch.setattr(notify.ntfy_client, "send", lambda **kwargs: True)
    user = {
        "user_id": 1,
        "username": "demo1",
        "full_name": "Demo One",
        "family_contact_phone": "0770000000",
    }
    result = notify.notify_emergency_family(user, ["chest pain"])
    assert result["ntfy"] is True
    assert result["sms"] is True


def test_notify_emergency_skips_sms_without_phone(seeded_db, monkeypatch):
    monkeypatch.setattr(notify.ntfy_client, "send", lambda **kwargs: True)
    user = {"user_id": 1, "username": "demo1", "family_contact_phone": ""}
    result = notify.notify_emergency_family(user, ["bleeding"])
    assert result["ntfy"] is True
    assert result["sms"] is None
