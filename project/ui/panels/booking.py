"""Booking panel - owned by Thevindu.

Displays booking suggestions and handles appointment confirmation flow.
Panel contract: render(user: dict) -> None
  - Reads from st.session_state["pending_booking"]
  - Modifies st.session_state as needed
  - Calls booking_agent and ntfy services
"""

import streamlit as st

from project.agents import booking_agent
from project.agents.basic_chatbot import _persist_message
from project.notifications.ntfy_client import send as ntfy_send, topic_for_user


def _get_disclaimer() -> str:
    """Get disclaimer text - placeholder for i18n integration."""
    from project.i18n.translate import t
    lang = st.session_state.get("user", {}).get("preferred_language", "en") or "en"
    return t("disclaimer.footer", lang)


def render(user: dict) -> None:
    """Render the booking panel with pending booking suggestions.
    
    Args:
        user: Current authenticated user dict
        
    Contract:
        - Reads st.session_state["pending_booking"]
        - May modify st.session_state["pending_booking"]
        - Calls booking_agent.book() for confirmations
        - Sends ntfy notifications on successful booking
        - Persists messages to chat history
    """
    pb = st.session_state.get("pending_booking")
    if not pb:
        return
    
    st.subheader("Booking suggestions")
    st.write(pb["message"])
    
    if not pb.get("alternatives"):
        st.info(
            "No available alternatives in the next week. "
            "Try another doctor or specialty."
        )
        if st.button("Dismiss", key="booking_dismiss_no_alts"):
            st.session_state.pop("pending_booking", None)
            st.rerun()
        return

    # Display each alternative slot with a Book button
    for alt in pb["alternatives"]:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{alt['doctor_name']}** @ {alt['facility_name']}  \n"
                f"{alt['date']} at {alt['time']} · Fee: LKR {alt['channeling_fee']:.0f}"
            )
        with col2:
            if st.button("Book", key=f"book_{alt['slot_id']}"):
                # Attempt to book the selected slot
                conf = booking_agent.book(user["user_id"], alt["slot_id"])
                if conf is None:
                    st.warning("That slot was just taken — please pick another.")
                else:
                    # Send ntfy notification
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
                    
                    # Persist confirmation to chat history
                    _persist_message(
                        user["user_id"], "assistant",
                        f"Appointment confirmed: {conf.doctor_name} at {conf.facility_name} on "
                        f"{conf.date} {conf.time}. (Appointment #{conf.appointment_id})",
                    )
                    
                    # Clean up session state and show success
                    st.session_state.pop("pending_booking", None)
                    st.success(
                        f"Booked with {conf.doctor_name} on {conf.date} at {conf.time}. "
                        "Push notification sent."
                    )
                    st.rerun()
    
    if st.button("Dismiss booking suggestions", key="booking_dismiss"):
        st.session_state.pop("pending_booking", None)
        st.rerun()
    
    st.markdown(_get_disclaimer())
