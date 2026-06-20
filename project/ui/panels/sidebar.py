"""Sidebar panel: user info, mock-data banner, ntfy topic, location, reminders, logout."""

from __future__ import annotations

import streamlit as st

from ..auth import logout
from ..common import get_geo
from ...agents import reminders
from ...i18n.translate import t
from ...notifications.ntfy_client import topic_for_user


def render(user: dict) -> None:
    lang = user.get("preferred_language", "en") or "en"
    with st.sidebar:
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")
        st.caption(f"Language: {lang}")

        st.warning(t("sidebar.mock_banner", lang))

        topic = topic_for_user(user["user_id"])
        st.markdown(f"**{t('sidebar.topic_label', lang)}**")
        st.code(topic, language="text")
        st.caption(t("sidebar.topic_caption", lang, topic=topic))

        st.divider()
        st.markdown(f"**{t('sidebar.location', lang)}**")
        try:
            from streamlit_geolocation import streamlit_geolocation  # type: ignore
            geo_val = streamlit_geolocation()
            if isinstance(geo_val, dict) and geo_val.get("latitude"):
                st.session_state["geo"] = geo_val
        except Exception:
            st.caption("(geolocation component unavailable — use manual entry below)")

        lat, lng = get_geo()
        if lat is not None and lng is not None:
            st.success(f"📍 {lat:.4f}, {lng:.4f}")
        else:
            st.info("Click the 📍 button above, or enter coordinates manually:")

        with st.expander(t("sidebar.location_manual", lang)):
            m_lat = st.number_input("Latitude",  value=6.9271, format="%.6f")
            m_lng = st.number_input("Longitude", value=79.8612, format="%.6f")
            if st.button(t("sidebar.use_coords", lang)):
                st.session_state["manual_geo"] = {"lat": m_lat, "lng": m_lng}
                st.rerun()

        st.divider()
        # Tier-3: TTS toggle.
        st.session_state["tts_on"] = st.toggle(
            t("sidebar.tts_toggle", lang),
            value=st.session_state.get("tts_on", False),
        )

        # Tier-3: reminder check button.
        if st.button(t("sidebar.reminders_btn", lang), use_container_width=True):
            due = reminders.due_within(user["user_id"], days=7)
            if not due:
                st.info(t("sidebar.reminders_none", lang))
            else:
                st.session_state["pending_reminders"] = [r["reminder_id"] for r in due]
                st.session_state["pending_reminders_count"] = len(due)

        pending_ids = st.session_state.get("pending_reminders")
        if pending_ids:
            count = st.session_state.get("pending_reminders_count", len(pending_ids))
            if st.button(t("sidebar.reminders_send", lang, n=count), type="primary", use_container_width=True):
                sent = reminders.fire(user["user_id"], pending_ids)
                st.success(t("sidebar.reminders_sent", lang, n=sent))
                st.session_state.pop("pending_reminders", None)
                st.session_state.pop("pending_reminders_count", None)

        st.divider()
        if st.button(t("sidebar.logout", lang)):
            logout()
            st.rerun()
