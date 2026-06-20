"""MedBridge AI — Streamlit entry point.

Run with:
    streamlit run project/ui/app.py

Flows wired here:
- Auth gate (login/signup)
- Sidebar: user info, mock-data banner, ntfy topic, location, logout
- Chat: persistent history, calls Basic Agent Chatbot
- Emergency: rule-based detection → confirm → tel:1990 link + ntfy push
- Booking: alternatives list, click-to-confirm + ntfy push
- Medicine: text-input pharmacy comparison table
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# Allow `streamlit run project/ui/app.py` to find the `project` package.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(_ROOT / "project" / ".env")
load_dotenv(_ROOT / ".env")  # fallback

from project.db.db import init_db  # noqa: E402
from project.ui.auth import current_user, logout, render_auth_gate  # noqa: E402
from project.agents import basic_chatbot, booking_agent, medicine_tracker  # noqa: E402
from project.notifications.ntfy_client import send as ntfy_send, topic_for_user  # noqa: E402

DISCLAIMER = (
    "_This is an AI-generated observation, not a medical diagnosis. "
    "Please consult a licensed physician or pharmacist._"
)

st.set_page_config(page_title="MedBridge AI", page_icon="🩺", layout="wide")

# Lazy DB init on first run.
if not st.session_state.get("_db_inited"):
    init_db(seed=True)
    st.session_state["_db_inited"] = True


# ---------- helpers ----------

def _get_geo() -> tuple[float | None, float | None]:
    geo = st.session_state.get("geo") or {}
    lat = geo.get("latitude") or geo.get("lat")
    lng = geo.get("longitude") or geo.get("lng")
    manual = st.session_state.get("manual_geo") or {}
    return (lat or manual.get("lat"), lng or manual.get("lng"))


def _render_sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")
        st.caption(f"Language: {user.get('preferred_language', 'en')}")

        st.warning("Demo build — all facility, doctor, slot, pharmacy and price data is SEED / MOCK data.")

        topic = topic_for_user(user["user_id"])
        st.markdown("**Family-alert push topic**")
        st.code(topic, language="text")
        st.caption(
            f"Family subscribes at https://ntfy.sh/{topic} (free, no signup) to get "
            "emergency notifications."
        )

        st.divider()
        st.markdown("**Your location** (for pharmacy distance)")
        try:
            from streamlit_geolocation import streamlit_geolocation  # type: ignore
            geo_val = streamlit_geolocation()
            if isinstance(geo_val, dict) and geo_val.get("latitude"):
                st.session_state["geo"] = geo_val
        except Exception:
            st.caption("(geolocation component unavailable — use manual entry below)")

        lat, lng = _get_geo()
        if lat is not None and lng is not None:
            st.success(f"📍 {lat:.4f}, {lng:.4f}")
        else:
            st.info("Click the 📍 button above, or enter coordinates manually:")

        with st.expander("Enter coordinates manually"):
            m_lat = st.number_input("Latitude",  value=6.9271, format="%.6f")
            m_lng = st.number_input("Longitude", value=79.8612, format="%.6f")
            if st.button("Use these coordinates"):
                st.session_state["manual_geo"] = {"lat": m_lat, "lng": m_lng}
                st.rerun()

        st.divider()
        if st.button("Log out"):
            logout()
            st.rerun()


# ---------- emergency panel ----------

def _render_emergency_panel(user: dict) -> None:
    em = st.session_state.get("pending_emergency")
    if not em:
        return
    st.error("🚨 **Possible medical emergency detected**")
    st.markdown(f"**Triggered by:** {', '.join(em.get('matched_terms', []))}")
    st.markdown(
        "If you confirm, MedBridge AI will show a tap-to-call link for Sri Lanka emergency "
        "services (**1990 Suwa Seriya**) and send a push notification to your saved family "
        "contact via ntfy.sh."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, this is an emergency", type="primary", use_container_width=True):
            st.session_state["emergency_confirmed"] = True
            topic = topic_for_user(user["user_id"])
            ok = ntfy_send(
                topic=topic,
                title="MedBridge AI: emergency alert",
                message=(
                    f"{user.get('full_name') or user['username']} flagged a possible emergency: "
                    f"{', '.join(em.get('matched_terms', []))}. They have been directed to dial 1990."
                ),
                user_id=user["user_id"],
                priority="urgent",
                tags=["rotating_light", "ambulance"],
                notif_type="emergency",
            )
            st.session_state["emergency_push_ok"] = ok
            # Persist the assistant turn so chat history reflects what happened.
            from project.agents.basic_chatbot import _persist_message
            _persist_message(
                user["user_id"], "assistant",
                "Emergency flow triggered. Please call 1990 immediately. Your family contact has been notified.",
            )
            st.rerun()
    with c2:
        if st.button("❌ No, false alarm", use_container_width=True):
            st.session_state.pop("pending_emergency", None)
            from project.agents.basic_chatbot import _persist_message
            _persist_message(
                user["user_id"], "assistant",
                "Understood — flagging as a false alarm. Tell me more about how you're feeling.",
            )
            st.rerun()

    if st.session_state.get("emergency_confirmed"):
        st.markdown("---")
        st.link_button(
            "📞  Call 1990 now (Suwa Seriya Ambulance)",
            "tel:1990",
            type="primary",
            use_container_width=True,
        )
        if st.session_state.get("emergency_push_ok"):
            st.success(f"Family contact notified at {datetime.now().strftime('%H:%M:%S')} via ntfy.sh.")
        else:
            st.warning("Family push notification could not be sent (logged regardless). Please call 1990.")
        if st.button("Dismiss and continue chatting"):
            for k in ("pending_emergency", "emergency_confirmed", "emergency_push_ok"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown(DISCLAIMER)


# ---------- booking panel ----------

def _render_pending_booking(user: dict) -> None:
    pb = st.session_state.get("pending_booking")
    if not pb:
        return
    st.subheader("Booking suggestions")
    st.write(pb["message"])
    if not pb.get("alternatives"):
        st.info("No available alternatives in the next week. Try another doctor or specialty.")
        if st.button("Dismiss"):
            st.session_state.pop("pending_booking", None)
            st.rerun()
        return

    for alt in pb["alternatives"]:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{alt['doctor_name']}** @ {alt['facility_name']}  \n"
                f"{alt['date']} at {alt['time']} · Fee: LKR {alt['channeling_fee']:.0f}"
            )
        with col2:
            if st.button("Book", key=f"book_{alt['slot_id']}"):
                conf = booking_agent.book(user["user_id"], alt["slot_id"])
                if conf is None:
                    st.warning("That slot was just taken — please pick another.")
                else:
                    topic = topic_for_user(user["user_id"])
                    ntfy_send(
                        topic=topic,
                        title="MedBridge AI: appointment confirmed",
                        message=(
                            f"Appointment #{conf.appointment_id} with {conf.doctor_name} at "
                            f"{conf.facility_name} on {conf.date} {conf.time}."
                        ),
                        user_id=user["user_id"],
                        tags=["calendar"],
                        notif_type="booking_confirmed",
                    )
                    from project.agents.basic_chatbot import _persist_message
                    _persist_message(
                        user["user_id"], "assistant",
                        f"Appointment confirmed: {conf.doctor_name} at {conf.facility_name} on "
                        f"{conf.date} {conf.time}. (Appointment #{conf.appointment_id})",
                    )
                    st.session_state.pop("pending_booking", None)
                    st.success(
                        f"Booked with {conf.doctor_name} on {conf.date} at {conf.time}. "
                        "Push notification sent."
                    )
                    st.rerun()
    if st.button("Dismiss booking suggestions"):
        st.session_state.pop("pending_booking", None)
        st.rerun()
    st.markdown(DISCLAIMER)


# ---------- medicine panel ----------

def _render_pending_medicine() -> None:
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
    st.markdown(DISCLAIMER)


# ---------- main ----------

def main() -> None:
    user = render_auth_gate()
    if not user:
        return

    _render_sidebar(user)

    st.title("🩺 MedBridge AI")
    st.caption("Multi-agent healthcare navigator — Tier 1 demo (Team Dream_4 · AgenTrix 2026)")

    # Show any active in-progress panels first so they're not buried under chat.
    _render_emergency_panel(user)
    _render_pending_booking(user)
    _render_pending_medicine()

    # ----- chat history -----
    history = basic_chatbot.load_history(user["user_id"], limit=50)
    for h in history:
        with st.chat_message(h["role"] if h["role"] in ("user", "assistant") else "assistant"):
            st.markdown(h["content"])

    user_text = st.chat_input("Describe your symptoms, or ask to book an appointment or check medicine prices…")
    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        result = basic_chatbot.handle(user["user_id"], user_text)

        if result.route == "emergency":
            st.session_state["pending_emergency"] = {
                "matched_terms": result.emergency.matched_terms if result.emergency else [],
            }
            st.rerun()

        # Render assistant reply.
        if result.reply:
            with st.chat_message("assistant"):
                st.markdown(result.reply)

        if result.route == "booking":
            ctx = booking_agent.BookingContext(user_id=user["user_id"], extracted=result.extracted)
            resp = booking_agent.process(ctx)
            st.session_state["pending_booking"] = {
                "message": resp.message,
                "alternatives": [a.model_dump() for a in resp.alternatives],
            }
            st.rerun()

        elif result.route == "medicine":
            lat, lng = _get_geo()
            ctx = medicine_tracker.MedicineContext(
                user_id=user["user_id"],
                raw_text=user_text,
                extracted_names=result.extracted.get("medicines"),
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
            st.rerun()

        elif result.route == "report_review":
            st.info("Report review (Specialist Panel + Moderator) is coming in Tier 2.")

    # Footer disclaimer always visible.
    st.markdown("---")
    st.markdown(DISCLAIMER)


if __name__ == "__main__":
    main()
else:
    # Streamlit imports this as a module on each rerun.
    main()
