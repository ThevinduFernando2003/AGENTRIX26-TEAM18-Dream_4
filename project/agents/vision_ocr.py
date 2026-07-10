"""Vision OCR helper — prescription transcription only.

Uses the provider selected by ``LLM_PROVIDER`` (Gemini Vision or OpenAI
vision-capable chat models) via ``project.llm``. Returns the transcription
as plain text. Never paraphrases, never invents dosage — the prompt asks
for an exact transcription, and the caller is expected to show the result
back to the user for explicit confirmation before acting on it (see
`medicine_tracker.process_prescription`).

Offline behaviour: returns `""` so the UI can show an honest
"vision unavailable" message and fall back to a paste-text path. We
never silently best-guess.
"""

from __future__ import annotations

import logging

from .. import llm

logger = logging.getLogger("medbridge.vision")

_PROMPT = (
    "Transcribe this prescription exactly as written. "
    "Preserve drug names, dosages, frequencies, and any handwritten notes "
    "verbatim. Do not summarise, interpret, or correct. Do not add any "
    "commentary or warnings. Return ONLY the transcription as plain text."
)


def is_available() -> bool:
    return llm.is_available()


def extract_prescription_text(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    if not is_available():
        return ""
    text = llm.ocr_image(image_bytes, mime_type, _PROMPT)
    if not text:
        logger.warning("Vision OCR returned empty transcription")
    return text
