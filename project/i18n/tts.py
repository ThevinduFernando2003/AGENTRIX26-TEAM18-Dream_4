"""gTTS wrapper — returns mp3 bytes for Streamlit's st.audio.

No API key required; gTTS uses Google Translate's public TTS endpoint.
Returns `None` on any failure so the UI can silently skip the audio
widget rather than crash.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger("medbridge.tts")

_LANG_MAP = {"en": "en", "si": "si", "ta": "ta"}
_MAX_CHARS = 2000


def speak(text: str, lang: str = "en") -> Optional[bytes]:
    text = (text or "").strip()
    if not text:
        return None
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]

    gtts_lang = _LANG_MAP.get(lang, "en")
    try:
        from gtts import gTTS  # type: ignore
        buf = io.BytesIO()
        gTTS(text=text, lang=gtts_lang).write_to_fp(buf)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("gTTS failed (%s): %s", gtts_lang, exc)
        return None
