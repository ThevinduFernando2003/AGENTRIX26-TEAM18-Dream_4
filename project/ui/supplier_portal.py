"""MedBridge Supplier Portal — concept demo (post-hackathon polish repo only).

Proves the two-sided platform model: pharmacies and hospitals publish their own
prices, stock, and appointment slots INTO MedBridge's data layer — the exact
tables the patient app already reads through its typed tools.

Run alongside the patient app:

    streamlit run project/ui/supplier_portal.py --server.port 8502

Phase 0: supplier login required; edits scoped to the bound pharmacy/facility.
Banner still labels concept / SEED data.
"""

from __future__ import annotations

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
from project import supplier_auth  # noqa: E402

st.set_page_config(page_title="MedBridge Supplier Portal", page_icon="🏪", layout="wide")

if not st.session_state.get("_db_inited"):
    init_db(seed=True)
    st.session_state["_db_inited"] = True

_SLOT_TIMES = [f"{h:02d}:{m}" for h in range(8, 20) for m in ("00", "30")]


# ---------- data helpers (plain SQL on the same tables the patient app reads) ----------


def _pharmacies(pharmacy_id: int | None = None) -> list[dict]:
    conn = get_conn()
    if pharmacy_id is not None:
        rows = conn.execute(
            "SELECT pharmacy_id, name, address FROM Pharmacy WHERE pharmacy_id = ?",
            (pharmacy_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT pharmacy_id, name, address FROM Pharmacy ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


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


def _apply_price_updates(account: dict, original: list[dict], edited: list[dict]) -> int:
    """UPDATE changed rows for the bound pharmacy only; returns how many changed."""
    conn = get_conn()
    before = {r["id"]: r for r in original}
    changed = 0
    with conn:
        for row in edited:
            prev = before.get(row["id"])
            if prev is None:
                continue
            if not supplier_auth.can_edit_price_row(account, row["id"]):
                continue
            new_price = float(row["price"])
            new_stock = 1 if row["in_stock"] else 0
            if new_price != prev["price"] or new_stock != prev["in_stock"]:
                conn.execute(
                    """UPDATE PharmacyMedicinePrice
                       SET price = ?, in_stock = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    (new_price, new_stock, row["id"]),
                )
                changed += 1
    return changed


def _doctors(facility_id: int | None = None) -> list[dict]:
    conn = get_conn()
    sql = """SELECT d.doctor_id, d.name, d.channeling_fee,
                    s.name AS specialty, f.name AS facility, d.facility_id
             FROM Doctor d
             JOIN Specialty s ON s.specialty_id = d.specialty_id
             JOIN Facility f ON f.facility_id = d.facility_id"""
    if facility_id is not None:
        rows = conn.execute(sql + " WHERE d.facility_id = ? ORDER BY d.name", (facility_id,)).fetchall()
    else:
        rows = conn.execute(sql + " ORDER BY d.name").fetchall()
    return [dict(r) for r in rows]


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


def _publish_slot(account: dict, doctor_id: int, day: str, time_hm: str) -> bool:
    """Insert a slot when allowed; False on deny or duplicate."""
    if not supplier_auth.can_publish_slot(account, doctor_id):
        return False
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


# ---------- login gate ----------


def _current_supplier() -> dict | None:
    return st.session_state.get("supplier_account")


def _gate() -> dict | None:
    account = _current_supplier()
    if account:
        return account

    st.title("🏪 MedBridge Supplier Portal")
    st.caption("Concept demo · SEED accounts — not live. Login required to edit.")
    with st.form("supplier_login"):
        username = st.text_input("Username", placeholder="union")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")
    if submitted:
        acc = supplier_auth.login(username, password)
        if acc:
            st.session_state["supplier_account"] = acc
            st.rerun()
        st.error("Invalid username or password.")
    st.info(
        "Demo logins: **union** / **unionpass** (Union Chemists) · "
        "**nawaloka** / **nawalokapass** (Nawaloka Hospital)"
    )
    return None


# ---------- page ----------


def main() -> None:
    account = _gate()
    if not account:
        return

    top = st.columns([5, 1])
    with top[0]:
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
    with top[1]:
        st.caption(f"Signed in as **{account['username']}** ({account['role']})")
        if st.button("Log out", use_container_width=True):
            st.session_state.pop("supplier_account", None)
            st.rerun()

    if account["role"] == "pharmacy":
        pharmacies = _pharmacies(account["pharmacy_id"])
        if not pharmacies:
            st.error("No pharmacy bound to this account.")
            return
        chosen = pharmacies[0]["pharmacy_id"]
        st.subheader(f"💊 {pharmacies[0]['name']}")
        rows = _price_rows(chosen)
        st.caption(
            "Edit a price or tick/untick stock, then publish. Scoped to your pharmacy only."
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
            n = _apply_price_updates(account, rows, edited)
            if n:
                st.success(f"{n} change(s) published — patients see this immediately.")
            else:
                st.info("No changes to publish.")

    elif account["role"] == "hospital":
        doctors = _doctors(account["facility_id"])
        if not doctors:
            st.error("No doctors at the facility bound to this account.")
            return
        st.subheader("🏥 Hospital dashboard")
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
                if _publish_slot(account, doc, day.isoformat(), time_hm):
                    st.success("Slot published — patients can book it immediately.")
                    st.rerun()
                else:
                    st.warning("Could not publish (denied or slot already exists).")
    else:
        st.error("Unknown supplier role.")

    st.markdown("---")
    st.caption(
        "Two-sided platform concept: suppliers publish INTO MedBridge, so the platform is the "
        "source of truth — no dependency on third-party APIs that don't exist in Sri Lanka. "
        "All data shown is SEED/demo data."
    )


main()
