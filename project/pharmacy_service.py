"""Pharmacy staff services — CSV import for prices/stock (Phase 1 / FR-PH03)."""

from __future__ import annotations

import csv
import io
from typing import Union

from . import authz
from .db.repo import connection as get_conn

CsvSource = Union[str, bytes]


def import_prices_csv(account: dict, csv_text: CsvSource) -> tuple[int, list[str]]:
    """Upsert price/stock rows for the bound pharmacy from CSV.

    Expected headers (case-insensitive): medicine, price, in_stock
    ``medicine`` must match a catalog Medicine.name exactly.
    Returns (rows_updated, error_messages). Never writes other pharmacies.
    """
    if not authz.is_pharmacy_staff(account) or not account.get("pharmacy_id"):
        return 0, ["Not authorized for pharmacy import."]
    pharmacy_id = int(account["pharmacy_id"])

    if isinstance(csv_text, bytes):
        try:
            csv_text = csv_text.decode("utf-8-sig")
        except UnicodeDecodeError:
            return 0, ["CSV must be UTF-8."]

    text = (csv_text or "").strip()
    if not text:
        return 0, ["Empty CSV."]

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return 0, ["CSV missing header row."]
    fields = { (f or "").strip().lower(): f for f in reader.fieldnames }
    for required in ("medicine", "price", "in_stock"):
        if required not in fields:
            return 0, [f"Missing required column: {required}"]

    conn = get_conn()
    med_lookup = {
        r["name"]: r["medicine_id"]
        for r in conn.execute("SELECT medicine_id, name FROM Medicine").fetchall()
    }

    updated = 0
    errors: list[str] = []
    with conn:
        for i, row in enumerate(reader, start=2):
            name = (row.get(fields["medicine"]) or "").strip()
            if not name:
                errors.append(f"Row {i}: empty medicine name.")
                continue
            mid = med_lookup.get(name)
            if mid is None:
                errors.append(f"Row {i}: unknown medicine {name!r}.")
                continue
            try:
                price = float(row.get(fields["price"]))
            except (TypeError, ValueError):
                errors.append(f"Row {i}: invalid price.")
                continue
            if price < 0:
                errors.append(f"Row {i}: price cannot be negative.")
                continue
            raw_stock = (row.get(fields["in_stock"]) or "").strip().lower()
            if raw_stock in ("1", "true", "yes", "y"):
                in_stock = 1
            elif raw_stock in ("0", "false", "no", "n"):
                in_stock = 0
            else:
                errors.append(f"Row {i}: in_stock must be true/false or 1/0.")
                continue

            # Defence: never trust a pharmacy_id column if present.
            existing = conn.execute(
                """SELECT id FROM PharmacyMedicinePrice
                   WHERE pharmacy_id = ? AND medicine_id = ?""",
                (pharmacy_id, mid),
            ).fetchone()
            if existing:
                conn.execute(
                    """UPDATE PharmacyMedicinePrice
                       SET price = ?, in_stock = ?, updated_at = datetime('now')
                       WHERE id = ? AND pharmacy_id = ?""",
                    (price, in_stock, existing["id"], pharmacy_id),
                )
            else:
                conn.execute(
                    """INSERT INTO PharmacyMedicinePrice
                       (pharmacy_id, medicine_id, price, in_stock, updated_at)
                       VALUES(?,?,?,?,datetime('now'))""",
                    (pharmacy_id, mid, price, in_stock),
                )
            updated += 1
    return updated, errors
