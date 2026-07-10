"""Sidebar panel: chat threads, language, location (city), family contact,
reminders, logout and rights notice."""

from __future__ import annotations

import streamlit as st

from ..auth import (
    invalidate_user_cache,
    logout,
    update_family_contact,
    update_preferred_language,
)
from ..common import (
    SRI_LANKA_CITIES,
    get_geo,
    language_short_label,
    nearest_city,
    render_sidebar_rights_banner,
)
from ...agents import basic_chatbot, reminders
from ...i18n.translate import t
from ...notifications.ntfy_client import topic_for_user

_LANG_OPTIONS = ["en", "si", "ta"]

# Panel state that belongs to a chat thread — cleared when a new chat starts.
_THREAD_STATE_KEYS = ("pending_booking", "pending_medicine", "pending_rx", "route_request")


def _render_conversations(user: dict, lang: str) -> None:
    """ChatGPT-style: a New-chat button + the user's past threads."""
    if st.button("➕ " + t("sidebar.new_chat", lang), use_container_width=True, key="new_chat"):
        st.session_state["active_conversation_id"] = None
        for k in _THREAD_STATE_KEYS:
            st.session_state.pop(k, None)
        st.rerun()

    convs = basic_chatbot.list_conversations(user["user_id"])
    if not convs:
        return
    st.caption(t("sidebar.chats", lang))
    active = st.session_state.get("active_conversation_id")
    for c in convs:
        title = c["title"] or t("sidebar.untitled_chat", lang)
        label = ("🟢 " if c["conversation_id"] == active else "💬 ") + title
        if st.button(label, key=f"conv_{c['conversation_id']}", use_container_width=True):
            st.session_state["active_conversation_id"] = c["conversation_id"]
            for k in _THREAD_STATE_KEYS:
                st.session_state.pop(k, None)
            st.rerun()


def render(user: dict) -> None:
    lang = user.get("preferred_language", "en") or "en"
    uid = user["user_id"]
    with st.sidebar:
        # ---- user header ----
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")

        # ---- chat threads ----
        _render_conversations(user, lang)

        # ---- language switcher ----
        st.divider()
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
            update_preferred_language(uid, selected_lang)
            invalidate_user_cache()
            st.rerun()

        # ---- location (city, not raw coordinates) ----
        st.divider()
        st.markdown(f"**{t('sidebar.location', lang)}**")
        try:
            from streamlit_geolocation import streamlit_geolocation  # type: ignore
            geo_val = streamlit_geolocation()
            if isinstance(geo_val, dict) and geo_val.get("latitude"):
                st.session_state["geo"] = geo_val
        except Exception:
            pass  # component unavailable → the city picker below still works

        picked = st.selectbox(
            t("sidebar.city", lang),
            ["—"] + list(SRI_LANKA_CITIES.keys()),
            key="city_pick",
        )
        if picked != "—":
            lat0, lng0 = SRI_LANKA_CITIES[picked]
            st.session_state["manual_geo"] = {"lat": lat0, "lng": lng0}

        lat, lng = get_geo()
        if lat is not None and lng is not None:
            st.success(t("sidebar.near_city", lang, city=nearest_city(lat, lng)))
        else:
            st.caption(t("sidebar.city_prompt", lang))

        # ---- family contact (used for the emergency push) ----
        st.divider()
        with st.expander(t("sidebar.family_contact", lang)):
            fc_name = st.text_input(
                t("auth.family_name", lang),
                value=user.get("family_contact_name") or "",
                key="fc_name",
            )
            fc_phone = st.text_input(
                t("auth.family_phone", lang),
                value=user.get("family_contact_phone") or "",
                key="fc_phone",
            )
            if st.button(t("sidebar.save_family", lang), key="save_fc", use_container_width=True):
                update_family_contact(uid, fc_name, fc_phone)
                invalidate_user_cache()
                st.success(t("sidebar.family_saved", lang))
                st.rerun()
            st.caption(t("sidebar.family_ntfy_hint", lang))
            st.code(f"https://ntfy.sh/{topic_for_user(uid)}", language=None)

        # ---- TTS toggle ----
        st.divider()
        st.session_state["tts_on"] = st.toggle(
            t("sidebar.tts_toggle", lang),
            value=st.session_state.get("tts_on", False),
        )

        # ---- reminders ----
        if st.button(t("sidebar.reminders_btn", lang), use_container_width=True):
            due = reminders.due_within(uid, days=7)
            if not due:
                st.info(t("sidebar.reminders_none", lang))
            else:
                st.session_state["pending_reminders"] = [r["reminder_id"] for r in due]
                st.session_state["pending_reminders_count"] = len(due)

        pending_ids = st.session_state.get("pending_reminders")
        if pending_ids:
            count = st.session_state.get("pending_reminders_count", len(pending_ids))
            if st.button(
                t("sidebar.reminders_send", lang, n=count), type="primary", use_container_width=True
            ):
                sent = reminders.fire(uid, pending_ids)
                st.success(t("sidebar.reminders_sent", lang, n=sent))
                st.session_state.pop("pending_reminders", None)
                st.session_state.pop("pending_reminders_count", None)

        # ---- logout + rights ----
        st.divider()
        if st.button(t("sidebar.logout", lang), use_container_width=True):
            logout()
            st.rerun()

        render_sidebar_rights_banner(lang)
