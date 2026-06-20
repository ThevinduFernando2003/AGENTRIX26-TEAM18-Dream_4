"""Medicine panel: pharmacy price/availability comparison for a routed medicine intent.

Owner: Nisal (Phase 2 grounds matching via the RAG retriever).

Flow:
1. Consume a ``route_request`` with route == "medicine" → run the medicine tracker
   and stash the result in ``st.session_state["pending_medicine"]``.
2. Render the pending pharmacy comparison table.
"""

from __future__ import annotations

import streamlit as st

from ..common import disclaimer, get_geo, lang_of
from ...agents import medicine_tracker
from ...i18n.translate import t, translate_dynamic


def _consume_route(user: dict) -> None:
    req = st.session_state.get("route_request")
    if not req or req.get("route") != "medicine":
        return
    lat, lng = get_geo()
    ctx = medicine_tracker.MedicineContext(
        user_id=user["user_id"],
        raw_text=req.get("raw_text", ""),
        extracted_names=(req.get("extracted") or {}).get("medicines"),
        user_lat=lat,
        user_lng=lng,
    )
    res = medicine_tracker.process(ctx)
    st.session_state["pending_medicine"] = {
        "message": res.message,
        "matched_names": res.matched_names,
        "unmatched_names": res.unmatched_names,
        "quotes": [q.model_dump() for q in res.quotes],
    }
    st.session_state.pop("route_request", None)
    st.rerun()


def render(user: dict) -> None:
    _consume_route(user)

    pm = st.session_state.get("pending_medicine")
    if not pm:
        return
    lang = lang_of(user)
    st.subheader(t("panel.medicine.title", lang))
    st.write(translate_dynamic(pm["message"], lang))
    if pm.get("matched_names"):
        st.caption(t("panel.medicine.matched", lang, names=", ".join(pm["matched_names"])))
    if pm.get("unmatched_names"):
        st.caption(t("panel.medicine.unmatched", lang, names=", ".join(pm["unmatched_names"])))
    if pm["quotes"]:
        col_pharmacy = t("panel.medicine.col_pharmacy", lang)
        col_address = t("panel.medicine.col_address", lang)
        col_items = t("panel.medicine.col_items", lang)
        col_total = t("panel.medicine.col_total", lang)
        col_distance = t("panel.medicine.col_distance", lang)
        col_missing = t("panel.medicine.col_missing", lang)
        table = []
        for q in pm["quotes"]:
            row = {
                col_pharmacy: q["pharmacy_name"],
                col_address: q.get("address") or "",
                col_items: ", ".join(f"{i['name']} (LKR {i['price']:.0f})" for i in q["items"]),
                col_total: f"{q['total_cost']:.0f}",
            }
            if q.get("distance_km") is not None:
                row[col_distance] = f"{q['distance_km']:.2f}"
            if q.get("missing"):
                row[col_missing] = ", ".join(q["missing"])
            table.append(row)
        st.dataframe(table, use_container_width=True, hide_index=True)
    if st.button(t("panel.medicine.dismiss", lang)):
        st.session_state.pop("pending_medicine", None)
        st.rerun()
    st.markdown(disclaimer(lang))
