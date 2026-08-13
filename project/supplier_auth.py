"""Supplier portal authentication — unified User RBAC (Phase 1).

Staff log into the supplier portal with the same User table as patients.
Only pharmacy_staff / hospital_staff / admin may enter the portal.
"""

from __future__ import annotations

from typing import Optional

import bcrypt

from . import authz
from .db.db import get_conn


def _verify_pw(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def login(username: str, password: str) -> Optional[dict]:
    """Return staff account dict on success, else None."""
    username = (username or "").strip()
    if not username or not password:
        return None
    conn = get_conn()
    row = conn.execute(
        """SELECT user_id, username, password_hash, role, pharmacy_id, facility_id
           FROM User WHERE username = ?""",
        (username,),
    ).fetchone()
    if not row or not _verify_pw(password, row["password_hash"]):
        return None
    account = authz.account_from_user_row(row)
    if not account or not authz.require_role(
        account, ("pharmacy_staff", "hospital_staff", "admin")
    ):
        return None
    # Portal session shape (supplier_id alias kept for older UI keys).
    return {
        "user_id": account["user_id"],
        "supplier_id": account["user_id"],
        "username": account["username"],
        "role": account["role"],
        "pharmacy_id": account.get("pharmacy_id"),
        "facility_id": account.get("facility_id"),
    }


def can_edit_pharmacy(account: dict | None, pharmacy_id: int) -> bool:
    return authz.can_edit_pharmacy(account, pharmacy_id)


def can_edit_price_row(account: dict | None, price_row_id: int) -> bool:
    return authz.can_edit_price_row(account, price_row_id)


def can_publish_slot(account: dict | None, doctor_id: int) -> bool:
    return authz.can_publish_slot(account, doctor_id)
