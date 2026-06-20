"""Gemini Vision OCR helper — prescription transcription only.

Free-tier `gemini-2.5-flash` supports image input. Returns the
transcription as plain text. Never paraphrases, never invents dosage —
the prompt asks for an exact transcription, and the caller is expected
to show the result back to the user for explicit confirmation before
acting on it (see `medicine_tracker.process_prescription`).

Offline behaviour: returns `""` so the UI can show an honest
"vision unavailable" message and fall back to a paste-text path. We
never silently best-guess.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("medbridge.vision")

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

_PROMPT = (
    "Transcribe this prescription exactly as written. "
    "Preserve drug names, dosages, frequencies, and any handwritten notes "
    "verbatim. Do not summarise, interpret, or correct. Do not add any "
    "commentary or warnings. Return ONLY the transcription as plain text."
)


def is_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def extract_prescription_text(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    if not is_available():
        return ""
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(_GEMINI_MODEL)
        image_part = {"mime_type": mime_type, "data": image_bytes}
        resp = model.generate_content([image_part, _PROMPT])
        text = (getattr(resp, "text", "") or "").strip()
        return text
    except Exception as exc:
        logger.warning("Gemini Vision OCR failed: %s", exc)
        return ""
