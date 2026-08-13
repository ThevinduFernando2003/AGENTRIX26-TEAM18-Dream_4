"""My Appointments panel — list confirmed bookings and cancel (Phase 0 / FR-P08).

Owner: Thevindu (booking domain). History stays read-only; this panel owns mutations.
"""

from __future__ import annotations

import streamlit as st

from ...agents import booking_agent
from ...agents.basic_chatbot import persist_message
from ...i18n.translate import t
from ...notifications.ntfy_client import send as ntfy_send, topic_for_user
from ..common import lang_of


def render(user: dict) -> None:
    lang = lang_of(user)
    appts = booking_agent.list_appointments(user["user_id"])
    if not appts:
        return

    with st.expander(t("panel.appointments.title", lang), expanded=False):
        st.caption(t("panel.appointments.hint", lang))
        for a in appts:
            aid = a["appointment_id"]
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(
                    t(
                        "panel.appointments.row",
                        lang,
                        id=aid,
                        doctor=a["doctor_name"],
                        facility=a["facility_name"],
                        date=a["date"],
                        time=a["time"],
                    )
                )
            with cols[1]:
                if st.button(
                    t("panel.appointments.cancel", lang),
                    key=f"cancel_appt_{aid}",
                    type="secondary",
                ):
                    conf = booking_agent.cancel(user["user_id"], aid)
                    if conf is None:
                        st.warning(t("panel.appointments.cancel_fail", lang))
                    else:
                        topic = topic_for_user(user["user_id"])
                        ntfy_send(
                            topic=topic,
                            title="MedBridge AI: appointment cancelled",
                            message=(
                                f"Appointment #{conf.appointment_id} with {conf.doctor_name} "
                                f"at {conf.facility_name} on {conf.date} {conf.time} was cancelled."
                            ),
                            user_id=user["user_id"],
                            tags=["calendar", "warning"],
                            notif_type="booking_cancelled",
                        )
                        persist_message(
                            user["user_id"],
                            "assistant",
                            (
                                f"Appointment cancelled: {conf.doctor_name} at {conf.facility_name} "
                                f"on {conf.date} {conf.time}. (Appointment #{conf.appointment_id})"
                            ),
                            conversation_id=st.session_state.get("active_conversation_id"),
                        )
                        st.success(
                            t(
                                "panel.appointments.cancelled",
                                lang,
                                doctor=conf.doctor_name,
                                date=conf.date,
                                time=conf.time,
                            )
                        )
                        st.rerun()
