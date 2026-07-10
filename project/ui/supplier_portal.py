"""MedBridge Supplier Portal — concept demo (post-hackathon polish repo only).

Proves the two-sided platform model: pharmacies and hospitals publish their own
prices, stock, and appointment slots INTO MedBridge's data layer — the exact
tables the patient app already reads through its typed tools. No third-party API
is involved because the platform itself is the source of truth (the
eChannelling / PickMe model).

Run alongside the patient app:

    streamlit run project/ui/supplier_portal.py --server.port 8502

Deliberate concept-demo scope: no supplier accounts (optional SUPPLIER_PASSCODE
env gate), English-only, SEED data clearly labeled. Production would add
supplier auth/roles and per-supplier scoping on these same tables.
"""

from __future__ import annotations

import os
import sys
from datetime import date as dtdate
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(_ROOT / "project" / ".env")

from project.db.db import get_conn, init_db  # noqa: E402

st.set_page_config(page_title="MedBridge Supplier Portal", page_icon="🏪", layout="wide")

if not st.session_state.get("_db_inited"):
    init_db(seed=True)
    st.session_state["_db_inited"] = True

_SLOT_TIMES = [f"{h:02d}:{m}" for h in range(8, 20) for m in ("00", "30")]


# ---------- data helpers (plain SQL on the same tables the patient app reads) ----------


def _pharmacies() -> list[dict]:
    conn = get_conn()
    return [
        dict(r)
        for r in conn.execute("SELECT pharmacy_id, name, address FROM Pharmacy ORDER BY name")
    ]


def _price_rows(pharmacy_id: int) -> list[dict]:
    conn = get_conn()
    return [
        dict(r)
        for r in conn.execute(
            """SELECT pmp.id, m.name AS medicine, pmp.price, pmp.in_stock
               FROM PharmacyMedicinePrice pmp
               JOIN Medicine m ON m.medicine_id = pmp.medicine_id
               WHERE pmp.pharmacy_id = ? ORDER BY m.name""",
            (pharmacy_id,),
        )
    ]


def _apply_price_updates(original: list[dict], edited: list[dict]) -> int:
    """UPDATE changed rows; returns how many rows changed."""
    conn = get_conn()
    before = {r["id"]: r for r in original}
    changed = 0
    with conn:
        for row in edited:
            prev = before.get(row["id"])
            if prev is None:
                continue
            new_price = float(row["price"])
            new_stock = 1 if row["in_stock"] else 0
            if new_price != prev["price"] or new_stock != prev["in_stock"]:
                conn.execute(
                    "UPDATE PharmacyMedicinePrice SET price = ?, in_stock = ? WHERE id = ?",
                    (new_price, new_stock, row["id"]),
                )
                changed += 1
    return changed


def _doctors() -> list[dict]:
    conn = get_conn()
    return [
        dict(r)
        for r in conn.execute(
            """SELECT d.doctor_id, d.name, d.channeling_fee,
                      s.name AS specialty, f.name AS facility
               FROM Doctor d
               JOIN Specialty s ON s.specialty_id = d.specialty_id
               JOIN Facility f ON f.facility_id = d.facility_id
               ORDER BY d.name"""
        )
    ]


def _upcoming_slots(doctor_id: int) -> list[dict]:
    conn = get_conn()
    return [
        dict(r)
        for r in conn.execute(
            """SELECT date, time,
                      CASE is_available WHEN 1 THEN '🟢 Available' ELSE '🔒 Booked' END AS status
               FROM AppointmentSlot
               WHERE doctor_id = ? AND date >= date('now')
               ORDER BY date, time LIMIT 40""",
            (doctor_id,),
        )
    ]


def _publish_slot(doctor_id: int, day: str, time_hm: str) -> bool:
    """Insert a slot; False when that (doctor, date, time) already exists.

    The schema has no UNIQUE on (doctor_id, date, time), so the duplicate
    check is done here before the INSERT.
    """
    conn = get_conn()
    exists = conn.execute(
        "SELECT 1 FROM AppointmentSlot WHERE doctor_id = ? AND date = ? AND time = ?",
        (doctor_id, day, time_hm),
    ).fetchone()
    if exists:
        return False
    with conn:
        conn.execute(
            "INSERT INTO AppointmentSlot(doctor_id, date, time, is_available) VALUES(?,?,?,1)",
            (doctor_id, day, time_hm),
        )
    return True


# ---------- optional passcode gate ----------


def _gate() -> bool:
    passcode = os.environ.get("SUPPLIER_PASSCODE", "").strip()
    if not passcode or st.session_state.get("_supplier_ok"):
        return True
    st.title("🏪 MedBridge Supplier Portal")
    entered = st.text_input("Supplier passcode", type="password")
    if entered and entered == passcode:
        st.session_state["_supplier_ok"] = True
        st.rerun()
    elif entered:
        st.error("Wrong passcode.")
    return False


# ---------- page ----------


def main() -> None:
    if not _gate():
        return

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #b45309 0%, #d97706 55%, #f59e0b 100%);
                    color: #fffbeb; border-radius: 16px; padding: 1.25rem 1.5rem; margin-bottom: 1rem;
                    box-shadow: 0 12px 30px rgba(217, 119, 6, 0.22);">
          <div style="font-size: 1.7rem; font-weight: 800;">🏪 MedBridge Supplier Portal</div>
          <div style="margin-top: .25rem; opacity: .92;">
            Suppliers publish prices, stock &amp; slots directly to the platform —
            patients see changes immediately. <b>Concept demo · SEED data, not live.</b>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_pharmacy, tab_hospital = st.tabs(["💊 Pharmacy dashboard", "🏥 Hospital dashboard"])

    # ---- Pharmacy: edit prices + stock ----
    with tab_pharmacy:
        pharmacies = _pharmacies()
        labels = {p["pharmacy_id"]: f"{p['name']} — {p['address']}" for p in pharmacies}
        chosen = st.selectbox(
            "Your pharmacy",
            options=list(labels),
            format_func=lambda pid: labels[pid],
            key="supplier_pharmacy",
        )
        rows = _price_rows(chosen)
        st.caption(
            "Edit a price or tick/untick stock, then publish. This writes the same "
            "PharmacyMedicinePrice rows the patient app's comparison reads."
        )
        edited = st.data_editor(
            rows,
            key=f"price_editor_{chosen}",
            use_container_width=True,
            hide_index=True,
            disabled=("id", "medicine"),
            column_order=("medicine", "price", "in_stock"),
            column_config={
                "medicine": st.column_config.TextColumn("Medicine"),
                "price": st.column_config.NumberColumn("Price (LKR)", min_value=0, step=1),
                "in_stock": st.column_config.CheckboxColumn("In stock"),
            },
        )
        if st.button("📣 Publish changes", type="primary", key="publish_prices"):
            n = _apply_price_updates(rows, edited)
            if n:
                st.success(f"{n} change(s) published — patients see this immediately.")
            else:
                st.info("No changes to publish.")

    # ---- Hospital: view + publish slots ----
    with tab_hospital:
        doctors = _doctors()
        dlabels = {
            d["doctor_id"]: f"{d['name']} — {d['specialty']} @ {d['facility']}" for d in doctors
        }
        doc = st.selectbox(
            "Doctor",
            options=list(dlabels),
            format_func=lambda did: dlabels[did],
            key="supplier_doctor",
        )
        col_list, col_form = st.columns([3, 2])
        with col_list:
            st.markdown("**Upcoming slots**")
            slots = _upcoming_slots(doc)
            if slots:
                st.dataframe(slots, use_container_width=True, hide_index=True)
            else:
                st.info("No upcoming slots published for this doctor yet.")
        with col_form:
            st.markdown("**Publish a new slot**")
            day = st.date_input("Date", min_value=dtdate.today(), key="slot_date")
            time_hm = st.selectbox("Time", _SLOT_TIMES, index=4, key="slot_time")
            if st.button("📣 Publish slot", type="primary", key="publish_slot"):
                if _publish_slot(doc, day.isoformat(), time_hm):
                    st.success("Slot published — patients can book it immediately.")
                    st.rerun()
                else:
                    st.warning("That slot already exists for this doctor.")

    st.markdown("---")
    st.caption(
        "Two-sided platform concept: suppliers publish INTO MedBridge, so the platform is the "
        "source of truth — no dependency on third-party APIs that don't exist in Sri Lanka. "
        "All data shown is SEED/demo data."
    )


main()
