"""Supplier portal login + org scoping (Phase 0/1 unified User RBAC)."""

from __future__ import annotations

from project import supplier_auth
from project.ui import supplier_portal as portal


def test_supplier_login_and_wrong_password(seeded_db):
    assert supplier_auth.login("union", "wrong") is None
    acc = supplier_auth.login("union", "unionpass")
    assert acc is not None
    assert acc["role"] == "pharmacy_staff"
    assert acc["pharmacy_id"] is not None


def test_pharmacy_cannot_edit_other_pharmacy(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    other = seeded_db.get_conn().execute(
        """SELECT id, pharmacy_id FROM PharmacyMedicinePrice
           WHERE pharmacy_id != ? LIMIT 1""",
        (union["pharmacy_id"],),
    ).fetchone()
    assert other is not None
    assert supplier_auth.can_edit_price_row(union, other["id"]) is False
    assert supplier_auth.can_edit_pharmacy(None, union["pharmacy_id"]) is False


def test_apply_price_updates_scoped(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    rows = portal._price_rows(union["pharmacy_id"])
    assert rows
    target = dict(rows[0])
    target["in_stock"] = not bool(target["in_stock"])
    edited = [target] + rows[1:]
    n = portal._apply_price_updates(union, rows, edited)
    assert n == 1

    foreign = seeded_db.get_conn().execute(
        """SELECT id, price, in_stock FROM PharmacyMedicinePrice
           WHERE pharmacy_id != ? LIMIT 1""",
        (union["pharmacy_id"],),
    ).fetchone()
    original = [
        {"id": foreign["id"], "price": float(foreign["price"]), "in_stock": bool(foreign["in_stock"])}
    ]
    spoofed = [
        {
            "id": foreign["id"],
            "price": float(foreign["price"]) + 99,
            "in_stock": bool(foreign["in_stock"]),
        }
    ]
    assert portal._apply_price_updates(union, original, spoofed) == 0


def test_hospital_slot_scope(seeded_db):
    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    assert hospital is not None
    assert hospital["role"] == "hospital_staff"
    own = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id = ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    other = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id != ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    assert supplier_auth.can_publish_slot(hospital, own["doctor_id"]) is True
    assert supplier_auth.can_publish_slot(hospital, other["doctor_id"]) is False
    assert portal._publish_slot(None, own["doctor_id"], "2099-01-01", "10:00") is False
