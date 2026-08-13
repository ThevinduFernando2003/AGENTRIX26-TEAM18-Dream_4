"""Phase 1 RBAC matrix — roles and org scoping."""

from __future__ import annotations

from project import authz, supplier_auth
from project.ui import auth


def test_staff_seeded_as_user_roles(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    assert union is not None
    assert union["role"] == "pharmacy_staff"
    assert union["pharmacy_id"] is not None

    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    assert hospital is not None
    assert hospital["role"] == "hospital_staff"
    assert hospital["facility_id"] is not None


def test_patient_cannot_use_supplier_portal(seeded_db):
    assert supplier_auth.login("demo1", "demo1pass") is None


def test_staff_cannot_use_patient_app_login(seeded_db):
    assert auth.login("union", "unionpass") is None
    assert auth.login("nawaloka", "nawalokapass") is None


def test_pharmacy_cannot_edit_other_org(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    other = seeded_db.get_conn().execute(
        """SELECT id FROM PharmacyMedicinePrice
           WHERE pharmacy_id != ? LIMIT 1""",
        (union["pharmacy_id"],),
    ).fetchone()
    assert authz.can_edit_price_row(union, other["id"]) is False
    assert authz.can_edit_pharmacy(None, union["pharmacy_id"]) is False


def test_patient_cannot_publish_slots(seeded_db):
    patient = {"role": "patient", "pharmacy_id": None, "facility_id": None}
    doc = seeded_db.get_conn().execute("SELECT doctor_id FROM Doctor LIMIT 1").fetchone()
    assert authz.can_publish_slot(patient, doc["doctor_id"]) is False


def test_hospital_scoped_to_facility(seeded_db):
    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    own = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id = ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    other = seeded_db.get_conn().execute(
        "SELECT doctor_id FROM Doctor WHERE facility_id != ? LIMIT 1",
        (hospital["facility_id"],),
    ).fetchone()
    assert authz.can_publish_slot(hospital, own["doctor_id"]) is True
    assert authz.can_publish_slot(hospital, other["doctor_id"]) is False


def test_signup_defaults_to_patient_role(seeded_db):
    ok, _ = auth.signup("rbac_patient", "secret123", consent_accepted=True)
    assert ok
    row = seeded_db.get_conn().execute(
        "SELECT role FROM User WHERE username = ?", ("rbac_patient",)
    ).fetchone()
    assert row["role"] == "patient"
