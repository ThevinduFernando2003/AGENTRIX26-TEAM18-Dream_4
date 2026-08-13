"""My Appointments panel — cancel + reschedule (Phase 0/1 / FR-P08, FR-P15).

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
            cols = st.columns([3, 1, 1])
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
            with cols[2]:
                if st.button(
                    t("panel.appointments.reschedule", lang),
                    key=f"resched_appt_{aid}",
                ):
                    st.session_state["reschedule_appointment_id"] = aid

        rid = st.session_state.get("reschedule_appointment_id")
        if rid:
            alts = booking_agent.alternatives_for_appointment(user["user_id"], rid)
            st.markdown(t("panel.appointments.reschedule_pick", lang))
            if not alts:
                st.info(t("panel.appointments.reschedule_none", lang))
            else:
                for alt in alts[:8]:
                    label = (
                        f"{alt.doctor_name} · {alt.facility_name} · {alt.date} {alt.time} "
                        f"(LKR {alt.channeling_fee:,.0f})"
                    )
                    if st.button(label, key=f"pick_resched_{rid}_{alt.slot_id}"):
                        conf = booking_agent.reschedule(
                            user["user_id"], rid, alt.slot_id
                        )
                        if conf is None:
                            st.warning(t("panel.appointments.reschedule_fail", lang))
                        else:
                            ntfy_send(
                                topic=topic_for_user(user["user_id"]),
                                title="MedBridge AI: appointment rescheduled",
                                message=(
                                    f"Moved to {conf.doctor_name} at {conf.facility_name} "
                                    f"on {conf.date} {conf.time}."
                                ),
                                user_id=user["user_id"],
                                tags=["calendar"],
                                notif_type="booking_rescheduled",
                            )
                            st.session_state.pop("reschedule_appointment_id", None)
                            st.success(
                                t(
                                    "panel.appointments.rescheduled",
                                    lang,
                                    doctor=conf.doctor_name,
                                    date=conf.date,
                                    time=conf.time,
                                )
                            )
                            st.rerun()
            if st.button(t("panel.appointments.reschedule_cancel_ui", lang), key="resched_dismiss"):
                st.session_state.pop("reschedule_appointment_id", None)
                st.rerun()
