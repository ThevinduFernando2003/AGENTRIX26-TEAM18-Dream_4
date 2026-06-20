"""ntfy.sh push notifications — free HTTP-POST topic broadcast.

Topic scheme: f"{NTFY_TOPIC_PREFIX}-{user_id}". The family member
subscribes to that topic from the ntfy mobile app or web at
https://ntfy.sh/{topic}.

Failures never raise to the caller — we log to NotificationLog and
return False so the chat/booking flow keeps moving.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

from ..db.db import get_conn

logger = logging.getLogger("medbridge.ntfy")

NTFY_BASE = os.environ.get("NTFY_BASE", "https://ntfy.sh")
TOPIC_PREFIX = os.environ.get("NTFY_TOPIC_PREFIX", "medbridge-demo")


def topic_for_user(user_id: int) -> str:
    return f"{TOPIC_PREFIX}-{user_id}"


def send(
    topic: str,
    title: str,
    message: str,
    *,
    user_id: Optional[int] = None,
    priority: str = "default",
    tags: Optional[list[str]] = None,
    notif_type: str = "generic",
) -> bool:
    url = f"{NTFY_BASE}/{topic}"
    headers = {
        "Title": title.encode("utf-8").decode("latin-1", errors="replace"),
        "Priority": priority,
    }
    if tags:
        headers["Tags"] = ",".join(tags)

    ok = False
    try:
        r = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=5)
        ok = 200 <= r.status_code < 300
        if not ok:
            logger.warning("ntfy non-2xx: %s %s", r.status_code, r.text[:200])
    except Exception as exc:  # network error, timeout, etc.
        logger.warning("ntfy send failed: %s", exc)

    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO NotificationLog(user_id, type, message, channel) VALUES(?,?,?,?)",
            (user_id, notif_type, f"[{title}] {message}", f"ntfy:{topic}"),
        )
        conn.commit()
    except Exception as exc:
        logger.warning("NotificationLog insert failed: %s", exc)

    return ok
