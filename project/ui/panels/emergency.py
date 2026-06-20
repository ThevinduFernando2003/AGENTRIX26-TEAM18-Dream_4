"""Emergency panel: rule-based detection → confirm → tel:1990 link + ntfy push.

Renders only when ``chat.py`` has flagged a possible emergency via
``st.session_state["pending_emergency"]``.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from ..common import disclaimer, lang_of
from ...agents.basic_chatbot import persist_message
from ...i18n.translate import t
from ...notifications.ntfy_client import send as ntfy_send, topic_for_user


def render(user: dict) -> None:
    em = st.session_state.get("pending_emergency")
    if not em:
        return
    lang = lang_of(user)
    st.error(f"**{t('em.title', lang)}**")
    st.markdown(f"**Triggered by:** {', '.join(em.get('matched_terms', []))}")
    st.markdown(
        "If you confirm, MedBridge AI will show a tap-to-call link for Sri Lanka emergency "
        "services (**1990 Suwa Seriya**) and send a push notification to your saved family "
        "contact via ntfy.sh."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(t("em.confirm", lang), type="primary", use_container_width=True):
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
            persist_message(
                user["user_id"], "assistant",
                "Emergency flow triggered. Please call 1990 immediately. Your family contact has been notified.",
            )
            st.rerun()
    with c2:
        if st.button(t("em.dismiss", lang), use_container_width=True):
            st.session_state.pop("pending_emergency", None)
            persist_message(
                user["user_id"], "assistant",
                "Understood — flagging as a false alarm. Tell me more about how you're feeling.",
            )
            st.rerun()

    if st.session_state.get("emergency_confirmed"):
        st.markdown("---")
        st.link_button(
            t("em.call_btn", lang),
            "tel:1990",
            type="primary",
            use_container_width=True,
        )
        if st.session_state.get("emergency_push_ok"):
            st.success(f"{t('em.family_notified', lang)} ({datetime.now().strftime('%H:%M:%S')})")
        else:
            st.warning("Family push notification could not be sent (logged regardless). Please call 1990.")
        if st.button("Dismiss and continue chatting"):
            for k in ("pending_emergency", "emergency_confirmed", "emergency_push_ok"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown(disclaimer(lang))
