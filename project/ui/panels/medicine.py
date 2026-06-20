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
    st.subheader("Pharmacy comparison")
    st.write(pm["message"])
    if pm.get("matched_names"):
        st.caption(f"Matched: {', '.join(pm['matched_names'])}")
    if pm.get("unmatched_names"):
        st.caption(f"Not in (demo) catalog: {', '.join(pm['unmatched_names'])}")
    if pm["quotes"]:
        table = []
        for q in pm["quotes"]:
            row = {
                "Pharmacy": q["pharmacy_name"],
                "Address": q.get("address") or "",
                "Items": ", ".join(f"{i['name']} (LKR {i['price']:.0f})" for i in q["items"]),
                "Total (LKR)": f"{q['total_cost']:.0f}",
            }
            if q.get("distance_km") is not None:
                row["Distance (km)"] = f"{q['distance_km']:.2f}"
            if q.get("missing"):
                row["Out of stock"] = ", ".join(q["missing"])
            table.append(row)
        st.dataframe(table, use_container_width=True, hide_index=True)
    if st.button("Dismiss medicine results"):
        st.session_state.pop("pending_medicine", None)
        st.rerun()
    st.markdown(disclaimer(lang_of(user)))
