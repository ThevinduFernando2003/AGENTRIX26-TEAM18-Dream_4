"""RBAC helpers (Phase 1 / FR-H02, FR-PH02).

Roles: patient · pharmacy_staff · hospital_staff · admin.
Staff org binding uses User.pharmacy_id / User.facility_id.
"""

from __future__ import annotations

from typing import Iterable, Optional

from .db.db import get_conn

ROLES = frozenset({"patient", "pharmacy_staff", "hospital_staff", "admin"})
STAFF_ROLES = frozenset({"pharmacy_staff", "hospital_staff", "admin"})


def normalize_role(role: str | None) -> str:
    r = (role or "patient").strip()
    return r if r in ROLES else "patient"


def require_role(account: dict | None, allowed: Iterable[str]) -> bool:
    if not account:
        return False
    return normalize_role(account.get("role")) in set(allowed)


def is_patient(account: dict | None) -> bool:
    return require_role(account, ("patient",))


def is_pharmacy_staff(account: dict | None) -> bool:
    return require_role(account, ("pharmacy_staff", "admin"))


def is_hospital_staff(account: dict | None) -> bool:
    return require_role(account, ("hospital_staff", "admin"))


def can_edit_pharmacy(account: dict | None, pharmacy_id: int) -> bool:
    if not account:
        return False
    role = normalize_role(account.get("role"))
    if role == "admin":
        return True
    if role != "pharmacy_staff":
        return False
    return account.get("pharmacy_id") == pharmacy_id


def can_manage_facility(account: dict | None, facility_id: int) -> bool:
    if not account:
        return False
    role = normalize_role(account.get("role"))
    if role == "admin":
        return True
    if role != "hospital_staff":
        return False
    return account.get("facility_id") == facility_id


def can_edit_price_row(account: dict | None, price_row_id: int) -> bool:
    if not is_pharmacy_staff(account) and not require_role(account, ("admin",)):
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
    if not account:
        return False
    conn = get_conn()
    row = conn.execute(
        "SELECT facility_id FROM Doctor WHERE doctor_id = ?",
        (doctor_id,),
    ).fetchone()
    if not row:
        return False
    return can_manage_facility(account, row["facility_id"])


def account_from_user_row(row) -> Optional[dict]:
    if row is None:
        return None
    d = dict(row)
    d["role"] = normalize_role(d.get("role"))
    return d
