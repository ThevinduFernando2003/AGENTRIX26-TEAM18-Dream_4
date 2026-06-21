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
    uid = user["user_id"]
    cid = st.session_state.get("active_conversation_id")

    # ----- chat history (bounded scroll box so the action panels above stay put) -----
    with st.container(height=440):
        history = basic_chatbot.load_history(uid, limit=200, conversation_id=cid) if cid else []
        if not history:
            # Friendly empty state for a brand-new chat.
            st.info(t("chat.quickstart", lang))
        for h in history:
            with st.chat_message(h["role"] if h["role"] in ("user", "assistant") else "assistant"):
                st.markdown(h["content"])

    # Tier-3: speak the previous turn's reply (queued before the rerun) when toggled.
    speak = st.session_state.pop("_speak_reply", None)
    if speak and st.session_state.get("tts_on"):
        audio_bytes = tts.speak(speak, lang=lang)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/mp3")

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

    # Lazily open a conversation on the first message (ChatGPT-style); title from it.
    if cid is None:
        cid = basic_chatbot.create_conversation(uid, title=user_text)
        st.session_state["active_conversation_id"] = cid

    with st.spinner(t("chat.thinking", lang)):
        result = basic_chatbot.handle(uid, user_text, preferred_language=lang, conversation_id=cid)

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

    # general / reminder: queue TTS, then rerun so the bounded history shows the
    # new turn (already persisted by handle()).
    if result.reply and st.session_state.get("tts_on"):
        st.session_state["_speak_reply"] = result.reply
    st.rerun()
