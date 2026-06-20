"""Gemini speech-to-text wrapper.

Sends an inline audio part to `gemini-2.5-flash` and asks for a
verbatim transcription in the speaker's language. Honest empty-string
fallback when GEMINI_API_KEY is absent — the UI then shows a "voice
input unavailable" message.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

logger = logging.getLogger("medbridge.stt")

LANG_NAMES = {"en": "English", "si": "Sinhala", "ta": "Tamil"}


def is_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def transcribe(audio_bytes: bytes, lang: str = "en", mime: str = "audio/wav") -> str:
    if not audio_bytes or not is_available():
        return ""
    lang_name = LANG_NAMES.get(lang, "English")
    prompt = (
        f"Transcribe the speech in this audio verbatim. The speaker is using "
        f"{lang_name}. Do NOT translate. Return ONLY the transcribed text — "
        "no quotes, no language label, no commentary."
    )
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
        audio_part = {"mime_type": mime, "data": audio_bytes}
        resp = model.generate_content([audio_part, prompt])
        return (getattr(resp, "text", "") or "").strip()
    except Exception as exc:
        logger.warning("STT failed: %s", exc)
        return ""
