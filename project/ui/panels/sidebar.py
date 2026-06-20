"""Sidebar panel: user info, mock-data banner, ntfy topic, location, language,
reminders, logout and rights notice."""

from __future__ import annotations

import streamlit as st

from ..auth import invalidate_user_cache, logout, update_preferred_language
from ..common import get_geo, language_short_label, render_sidebar_rights_banner
from ...agents import reminders
from ...i18n.translate import t
from ...notifications.ntfy_client import topic_for_user

_LANG_OPTIONS = ["en", "si", "ta"]


def render(user: dict) -> None:
    lang = user.get("preferred_language", "en") or "en"
    with st.sidebar:
        # ---- user header ----
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")

        # ---- language switcher ----
        st.markdown(f"**{t('sidebar.language', lang)}**")
        selected_lang = st.radio(
            t("sidebar.language", lang),
            _LANG_OPTIONS,
            index=_LANG_OPTIONS.index(lang) if lang in _LANG_OPTIONS else 0,
            format_func=language_short_label,
            horizontal=True,
            key="lang_switcher",
            label_visibility="collapsed",
        )
        if selected_lang != lang:
            update_preferred_language(user["user_id"], selected_lang)
            invalidate_user_cache()
            st.rerun()

        st.warning(t("sidebar.mock_banner", lang))

        # ---- ntfy topic ----
        topic = topic_for_user(user["user_id"])
        st.markdown(f"**{t('sidebar.topic_label', lang)}**")
        st.code(topic, language="text")
        st.caption(t("sidebar.topic_caption", lang, topic=topic))

        # ---- location ----
        st.divider()
        st.markdown(f"**{t('sidebar.location', lang)}**")
        try:
            from streamlit_geolocation import streamlit_geolocation  # type: ignore
            geo_val = streamlit_geolocation()
            if isinstance(geo_val, dict) and geo_val.get("latitude"):
                st.session_state["geo"] = geo_val
        except Exception:
            st.caption(t("sidebar.geo_unavail", lang))

        lat, lng = get_geo()
        if lat is not None and lng is not None:
            st.success(f"📍 {lat:.4f}, {lng:.4f}")
        else:
            st.info(t("sidebar.geo_prompt", lang))

        with st.expander(t("sidebar.location_manual", lang)):
            m_lat = st.number_input(t("sidebar.lat", lang),  value=6.9271, format="%.6f")
            m_lng = st.number_input(t("sidebar.lng", lang), value=79.8612, format="%.6f")
            if st.button(t("sidebar.use_coords", lang)):
                st.session_state["manual_geo"] = {"lat": m_lat, "lng": m_lng}
                st.rerun()

        # ---- TTS toggle ----
        st.divider()
        st.session_state["tts_on"] = st.toggle(
            t("sidebar.tts_toggle", lang),
            value=st.session_state.get("tts_on", False),
        )

        # ---- reminders ----
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

        # ---- logout + rights ----
        st.divider()
        if st.button(t("sidebar.logout", lang), use_container_width=True):
            logout()
            st.rerun()

        render_sidebar_rights_banner(lang)
