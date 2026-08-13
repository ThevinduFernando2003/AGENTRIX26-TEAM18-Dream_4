"""High-level notification orchestration (Phase 1)."""

from __future__ import annotations

from typing import Optional

from . import ntfy_client, sms_client


def notify_emergency_family(
    user: dict,
    matched_terms: list[str],
) -> dict:
    """Push ntfy (always attempted) + SMS to family phone when present.

    Returns ``{"ntfy": bool, "sms": bool | None}`` where ``sms`` is None when
    no family phone is configured.
    """
    terms = ", ".join(matched_terms) if matched_terms else "unspecified"
    name = user.get("full_name") or user.get("username") or "A patient"
    uid = user.get("user_id")
    message = (
        f"{name} flagged a possible emergency: {terms}. "
        f"They have been directed to dial 1990."
    )

    ntfy_ok = ntfy_client.send(
        topic=ntfy_client.topic_for_user(int(uid)),
        title="MedBridge AI: emergency alert",
        message=message,
        user_id=uid,
        priority="urgent",
        tags=["rotating_light", "ambulance"],
        notif_type="emergency",
    )

    phone = (user.get("family_contact_phone") or "").strip()
    sms_ok: Optional[bool]
    if phone:
        sms_ok = sms_client.send_sms(
            phone,
            f"MedBridge EMERGENCY: {message}",
            user_id=uid,
            notif_type="emergency_sms",
        )
    else:
        sms_ok = None

    return {"ntfy": ntfy_ok, "sms": sms_ok}
