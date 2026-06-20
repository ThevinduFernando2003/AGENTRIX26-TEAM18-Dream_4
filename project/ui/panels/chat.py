"""Chat panel: persistent history, voice input, and the intent router.

Owner: Janidu. This is the only panel that talks to ``basic_chatbot.handle``. It
never imports a domain agent — instead it writes a one-shot ``route_request`` to
``st.session_state`` (see the panel-contract docstring in ``panels/__init__``) and
lets each domain panel pick up its own work.
"""

from __future__ import annotations

import streamlit as st

from ..common import lang_of
from ...agents import basic_chatbot
from ...i18n import stt, tts
from ...i18n.translate import t

_DOMAIN_ROUTES = {"booking", "medicine", "report_review"}


def render(user: dict) -> None:
    lang = lang_of(user)

    # ----- chat history -----
    history = basic_chatbot.load_history(user["user_id"], limit=50)
    if not history:
        # Friendly empty state so a first-time user knows what to try.
        st.info(t("chat.quickstart", lang))
    for h in history:
        with st.chat_message(h["role"] if h["role"] in ("user", "assistant") else "assistant"):
            st.markdown(h["content"])

    # ----- Tier-3 voice input -----
    with st.expander(t("chat.voice_expander", lang), expanded=False):
        if not stt.is_available():
            st.info(t("chat.voice_unavail", lang))
        audio = st.audio_input("🎙️", key="voice_in")
        if audio is not None and st.button(t("chat.voice_transcribe", lang), key="voice_send"):
            mime = getattr(audio, "type", None) or "audio/wav"
            with st.spinner(t("chat.voice_transcribing", lang)):
                transcript = stt.transcribe(audio.read(), lang=lang, mime=mime)
            if transcript:
                st.session_state["_queued_user_text"] = transcript
                st.rerun()
            else:
                st.warning(t("chat.voice_failed", lang))

    user_text = st.session_state.pop("_queued_user_text", None) or st.chat_input(t("chat.placeholder", lang))
    if not user_text:
        return

    with st.chat_message("user"):
        st.markdown(user_text)
    # Echo the user turn above immediately, then show a spinner while the router
    # runs so the chat never looks frozen (heuristic-first keeps this near-instant).
    with st.spinner(t("chat.thinking", lang)):
        result = basic_chatbot.handle(user["user_id"], user_text, preferred_language=lang)

    if result.route == "emergency":
        st.session_state["pending_emergency"] = {
            "matched_terms": result.emergency.matched_terms if result.emergency else [],
        }
        st.rerun()

    # Hand off domain intents to their own panel via the decoupled route signal.
    if result.route in _DOMAIN_ROUTES:
        st.session_state["route_request"] = {
            "route": result.route,
            "extracted": result.extracted,
            "raw_text": user_text,
        }
        st.rerun()

    # general / reminder: reply is shown inline (and already persisted by handle()).
    if result.reply:
        with st.chat_message("assistant"):
            st.markdown(result.reply)
            # Tier-3: speak the reply when toggle is on.
            if st.session_state.get("tts_on"):
                audio_bytes = tts.speak(result.reply, lang=lang)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
