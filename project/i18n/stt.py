"""Speech-to-text wrapper.

Uses the provider selected by ``LLM_PROVIDER`` via ``project.llm``: an inline
audio part to Gemini, or the dedicated Whisper transcription endpoint on
OpenAI. Honest empty-string fallback when no API key is configured — the UI
then shows a "voice input unavailable" message.
"""

from __future__ import annotations

import logging

from .. import llm

logger = logging.getLogger("medbridge.stt")

LANG_NAMES = {"en": "English", "si": "Sinhala", "ta": "Tamil"}


def is_available() -> bool:
    return llm.is_available()


def transcribe(audio_bytes: bytes, lang: str = "en", mime: str = "audio/wav") -> str:
    if not audio_bytes or not is_available():
        return ""
    lang_name = LANG_NAMES.get(lang, "English")
    prompt = (
        f"Transcribe the speech in this audio verbatim. The speaker is using "
        f"{lang_name}. Do NOT translate. Return ONLY the transcribed text — "
        "no quotes, no language label, no commentary."
    )
    return llm.transcribe_audio(audio_bytes, mime, prompt, lang=lang)
