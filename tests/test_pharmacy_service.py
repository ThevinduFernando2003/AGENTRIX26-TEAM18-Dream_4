"""Pharmacy CSV import — happy path + org isolation."""

from __future__ import annotations

from project import pharmacy_service, supplier_auth


_CSV = """medicine,price,in_stock
Paracetamol 500mg,99,true
Losartan 50mg,18,true
"""


def test_csv_import_updates_bound_pharmacy(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    n, errs = pharmacy_service.import_prices_csv(union, _CSV)
    assert n == 2
    assert errs == []
    row = seeded_db.get_conn().execute(
        """SELECT pmp.price, pmp.in_stock, pmp.updated_at, pmp.pharmacy_id
           FROM PharmacyMedicinePrice pmp
           JOIN Medicine m ON m.medicine_id = pmp.medicine_id
           WHERE pmp.pharmacy_id = ? AND m.name = 'Paracetamol 500mg'""",
        (union["pharmacy_id"],),
    ).fetchone()
    assert float(row["price"]) == 99.0
    assert row["in_stock"] == 1
    assert row["updated_at"]


def test_csv_rejects_unknown_medicine_and_hospital(seeded_db):
    union = supplier_auth.login("union", "unionpass")
    n, errs = pharmacy_service.import_prices_csv(
        union, "medicine,price,in_stock\nNot A Real Drug,1,true\n"
    )
    assert n == 0
    assert any("unknown medicine" in e for e in errs)

    hospital = supplier_auth.login("nawaloka", "nawalokapass")
    n2, errs2 = pharmacy_service.import_prices_csv(hospital, _CSV)
    assert n2 == 0
    assert errs2


def test_csv_cannot_target_other_pharmacy_column(seeded_db):
    """Even if CSV invents pharmacy_id, writes stay on the bound pharmacy."""
    union = supplier_auth.login("union", "unionpass")
    other_id = seeded_db.get_conn().execute(
        "SELECT pharmacy_id FROM Pharmacy WHERE pharmacy_id != ? LIMIT 1",
        (union["pharmacy_id"],),
    ).fetchone()["pharmacy_id"]
    before = seeded_db.get_conn().execute(
        """SELECT price FROM PharmacyMedicinePrice pmp
           JOIN Medicine m ON m.medicine_id = pmp.medicine_id
           WHERE pmp.pharmacy_id = ? AND m.name = 'Paracetamol 500mg'""",
        (other_id,),
    ).fetchone()["price"]
    csv = (
        "medicine,price,in_stock,pharmacy_id\n"
        f"Paracetamol 500mg,12345,true,{other_id}\n"
    )
    n, _ = pharmacy_service.import_prices_csv(union, csv)
    assert n == 1
    after = seeded_db.get_conn().execute(
        """SELECT price FROM PharmacyMedicinePrice pmp
           JOIN Medicine m ON m.medicine_id = pmp.medicine_id
           WHERE pmp.pharmacy_id = ? AND m.name = 'Paracetamol 500mg'""",
        (other_id,),
    ).fetchone()["price"]
    assert float(after) == float(before)
