"""Supplier portal authentication + org scoping (Phase 0 / FR-H01, FR-PH01)."""

from __future__ import annotations

from typing import Optional

import bcrypt

from .db.db import get_conn


def _verify_pw(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def login(username: str, password: str) -> Optional[dict]:
    """Return supplier account dict on success, else None."""
    username = (username or "").strip()
    if not username or not password:
        return None
    conn = get_conn()
    row = conn.execute(
        """SELECT supplier_id, username, password_hash, role, pharmacy_id, facility_id
           FROM SupplierAccount WHERE username = ?""",
        (username,),
    ).fetchone()
    if not row or not _verify_pw(password, row["password_hash"]):
        return None
    return {
        "supplier_id": row["supplier_id"],
        "username": row["username"],
        "role": row["role"],
        "pharmacy_id": row["pharmacy_id"],
        "facility_id": row["facility_id"],
    }


def can_edit_pharmacy(account: dict | None, pharmacy_id: int) -> bool:
    if not account or account.get("role") != "pharmacy":
        return False
    return account.get("pharmacy_id") == pharmacy_id


def can_edit_price_row(account: dict | None, price_row_id: int) -> bool:
    if not account or account.get("role") != "pharmacy":
        return False
    conn = get_conn()
    row = conn.execute(
        "SELECT pharmacy_id FROM PharmacyMedicinePrice WHERE id = ?",
        (price_row_id,),
    ).fetchone()
    if not row:
        return False
    return can_edit_pharmacy(account, row["pharmacy_id"])


def can_publish_slot(account: dict | None, doctor_id: int) -> bool:
    if not account or account.get("role") != "hospital":
        return False
    conn = get_conn()
    row = conn.execute(
        "SELECT facility_id FROM Doctor WHERE doctor_id = ?",
        (doctor_id,),
    ).fetchone()
    if not row:
        return False
    return account.get("facility_id") == row["facility_id"]
