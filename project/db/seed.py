"""Idempotent seed loader.

Run from init_db() if the User table is empty. Re-running is safe:
existing usernames / medicines / pharmacies are skipped.

Every seed JSON carries a top-level "_note: SEED DATA — not live"; the
loader logs that label on insert so the source of the rows is obvious.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import bcrypt

from .db import get_conn

logger = logging.getLogger("medbridge.seed")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

_KB = Path(__file__).resolve().parent.parent / "kb"


def _hash_pw(plain: str) -> str:
    # bcrypt has a 72-byte input limit; truncate defensively.
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _load(name: str) -> dict:
    with open(_KB / name, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Loading %s — %s", name, data.get("_note", "(no label)"))
    return data


def _resolve_date(day_offset: int) -> str:
    return (date.today() + timedelta(days=day_offset)).isoformat()


def _seed_users() -> None:
    conn = get_conn()
    data = _load("seed_users.json")
    for u in data["users"]:
        row = conn.execute("SELECT user_id FROM User WHERE username = ?", (u["username"],)).fetchone()
        if row:
            continue
        conn.execute(
            """INSERT INTO User(username, password_hash, full_name, age, gender,
                                preferred_language, family_contact_name, family_contact_phone)
               VALUES(?,?,?,?,?,?,?,?)""",
            (
                u["username"],
                _hash_pw(u["password"]),
                u.get("full_name"),
                u.get("age"),
                u.get("gender"),
                u.get("preferred_language", "en"),
                u.get("family_contact_name"),
                u.get("family_contact_phone"),
            ),
        )
    conn.commit()


def _seed_facilities() -> None:
    conn = get_conn()
    data = _load("seed_facilities.json")

    specialty_ids: dict[str, int] = {}
    for s in data["specialties"]:
        row = conn.execute("SELECT specialty_id FROM Specialty WHERE name = ?", (s["name"],)).fetchone()
        if row:
            specialty_ids[s["name"]] = row["specialty_id"]
            continue
        cur = conn.execute("INSERT INTO Specialty(name, description) VALUES(?,?)", (s["name"], s.get("description")))
        specialty_ids[s["name"]] = cur.lastrowid

    for fac in data["facilities"]:
        row = conn.execute("SELECT facility_id FROM Facility WHERE name = ? AND address = ?",
                           (fac["name"], fac.get("address"))).fetchone()
        if row:
            facility_id = row["facility_id"]
        else:
            cur = conn.execute(
                "INSERT INTO Facility(name, type, address, lat, lng, phone) VALUES(?,?,?,?,?,?)",
                (fac["name"], fac.get("type"), fac.get("address"), fac.get("lat"), fac.get("lng"), fac.get("phone")),
            )
            facility_id = cur.lastrowid

        for doc in fac.get("doctors", []):
            row = conn.execute("SELECT doctor_id FROM Doctor WHERE name = ? AND facility_id = ?",
                               (doc["name"], facility_id)).fetchone()
            if row:
                doctor_id = row["doctor_id"]
            else:
                cur = conn.execute(
                    "INSERT INTO Doctor(facility_id, specialty_id, name, channeling_fee) VALUES(?,?,?,?)",
                    (facility_id, specialty_ids[doc["specialty"]], doc["name"], doc.get("channeling_fee", 0)),
                )
                doctor_id = cur.lastrowid

            for slot in doc.get("slots", []):
                slot_date = _resolve_date(slot["day_offset"])
                row = conn.execute(
                    "SELECT slot_id FROM AppointmentSlot WHERE doctor_id = ? AND date = ? AND time = ?",
                    (doctor_id, slot_date, slot["time"]),
                ).fetchone()
                if row:
                    continue
                conn.execute(
                    "INSERT INTO AppointmentSlot(doctor_id, date, time, is_available) VALUES(?,?,?,?)",
                    (doctor_id, slot_date, slot["time"], 1 if slot.get("is_available", True) else 0),
                )
    conn.commit()


def _seed_medicines() -> None:
    conn = get_conn()
    data = _load("seed_medicines.json")
    for m in data["medicines"]:
        row = conn.execute("SELECT medicine_id FROM Medicine WHERE name = ?", (m["name"],)).fetchone()
        if row:
            continue
        conn.execute(
            "INSERT INTO Medicine(name, reference_dosage_text) VALUES(?,?)",
            (m["name"], m.get("reference_dosage_text")),
        )
    conn.commit()


def _seed_pharmacies() -> None:
    conn = get_conn()
    data = _load("seed_pharmacy_prices.json")
    for ph in data["pharmacies"]:
        row = conn.execute("SELECT pharmacy_id FROM Pharmacy WHERE name = ?", (ph["name"],)).fetchone()
        if row:
            pharmacy_id = row["pharmacy_id"]
        else:
            cur = conn.execute(
                "INSERT INTO Pharmacy(name, address, lat, lng) VALUES(?,?,?,?)",
                (ph["name"], ph.get("address"), ph.get("lat"), ph.get("lng")),
            )
            pharmacy_id = cur.lastrowid

        for med_name, info in ph.get("prices", {}).items():
            med = conn.execute("SELECT medicine_id FROM Medicine WHERE name = ?", (med_name,)).fetchone()
            if not med:
                logger.warning("Skipping price for unknown medicine %s", med_name)
                continue
            exists = conn.execute(
                "SELECT id FROM PharmacyMedicinePrice WHERE pharmacy_id = ? AND medicine_id = ?",
                (pharmacy_id, med["medicine_id"]),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO PharmacyMedicinePrice(pharmacy_id, medicine_id, price, in_stock) VALUES(?,?,?,?)",
                (pharmacy_id, med["medicine_id"], info["price"], 1 if info.get("in_stock", True) else 0),
            )
    conn.commit()


def load_seed_if_empty() -> None:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS n FROM User").fetchone()
    if row["n"] > 0:
        logger.info("Users exist — skipping seed.")
        return
    logger.info("Empty DB detected — loading SEED DATA (not live).")
    _seed_users()
    _seed_facilities()
    _seed_medicines()
    _seed_pharmacies()
    logger.info("Seed complete.")


if __name__ == "__main__":
    from .db import init_db
    init_db(seed=True)
