"""SMS gateway adapter for emergency family alerts (Phase 1 / FR-F01).

Providers (env ``SMS_PROVIDER``):
- ``stub`` (default) — offline-safe; logs to NotificationLog, returns success
  when ``SMS_STUB_OK`` is not ``0``.
- ``http`` — POST JSON ``{to, from, message}`` to ``SMS_HTTP_URL`` with optional
  ``Authorization: Bearer {SMS_HTTP_TOKEN}``.

Never raises to callers.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

from ..db.repo import connection as get_conn

logger = logging.getLogger("medbridge.sms")


def send_sms(
    to_phone: str,
    message: str,
    *,
    user_id: Optional[int] = None,
    notif_type: str = "emergency_sms",
) -> bool:
    to_phone = (to_phone or "").strip()
    if not to_phone or not (message or "").strip():
        return False

    provider = os.environ.get("SMS_PROVIDER", "stub").strip().lower() or "stub"
    ok = False
    channel = f"sms:{provider}"

    if provider == "stub":
        ok = os.environ.get("SMS_STUB_OK", "1").strip() != "0"
        logger.info("SMS stub → %s (%s)", to_phone, "ok" if ok else "fail")
    elif provider == "http":
        url = os.environ.get("SMS_HTTP_URL", "").strip()
        if not url:
            logger.warning("SMS_PROVIDER=http but SMS_HTTP_URL unset")
        else:
            headers = {"Content-Type": "application/json"}
            token = os.environ.get("SMS_HTTP_TOKEN", "").strip()
            if token:
                headers["Authorization"] = f"Bearer {token}"
            payload = {
                "to": to_phone,
                "from": os.environ.get("SMS_FROM", "MedBridge"),
                "message": message,
            }
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=8)
                ok = 200 <= r.status_code < 300
                if not ok:
                    logger.warning("SMS HTTP non-2xx: %s %s", r.status_code, r.text[:200])
            except Exception as exc:
                logger.warning("SMS HTTP failed: %s", exc)
    else:
        logger.warning("Unknown SMS_PROVIDER %r", provider)

    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO NotificationLog(user_id, type, message, channel) VALUES(?,?,?,?)",
            (user_id, notif_type, f"[SMS→{to_phone}] {message}", channel),
        )
        conn.commit()
    except Exception as exc:
        logger.warning("NotificationLog insert failed: %s", exc)

    return ok
