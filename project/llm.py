"""Provider-agnostic LLM access layer.

``LLM_PROVIDER`` in the environment selects the backend for every model call in
the app — chat routing, dynamic translation, vision OCR, speech-to-text, the
CrewAI specialist panel/moderator, and the Pydantic AI booking agent:

- ``gemini`` (default): Google Gemini via ``google-generativeai``.
- ``openai``: OpenAI via the official ``openai`` SDK.

Flipping provider is a one-line ``.env`` change; no code changes anywhere else.

Every helper keeps the app's graceful-offline contract: missing key, missing
library, timeout, or network failure returns ``""``/``None`` and never raises,
so all deterministic fallbacks keep working exactly as before.
"""

from __future__ import annotations

import base64
import io
import logging
import os

logger = logging.getLogger("medbridge.llm")

_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_DEFAULT_OPENAI_STT_MODEL = "whisper-1"


def provider() -> str:
    """Active provider name: 'openai' or 'gemini' (default)."""
    return "openai" if os.environ.get("LLM_PROVIDER", "").strip().lower() == "openai" else "gemini"


def api_key() -> str | None:
    if provider() == "openai":
        return os.environ.get("OPENAI_API_KEY") or None
    return os.environ.get("GEMINI_API_KEY") or None


def is_available() -> bool:
    """True when the active provider has a key. Gates every online feature."""
    return bool(api_key())


def model_name() -> str:
    if provider() == "openai":
        return os.environ.get("OPENAI_MODEL", _DEFAULT_OPENAI_MODEL)
    return os.environ.get("GEMINI_MODEL", _DEFAULT_GEMINI_MODEL)


def crewai_model() -> str:
    """Model string for CrewAI's LLM (litellm format: '<provider>/<model>')."""
    return f"{provider()}/{model_name()}"


def _openai_client(timeout_s: float):
    from openai import OpenAI  # type: ignore

    # max_retries=0 matches the app-wide fail-fast design: on a throttled or
    # broken key we fall back to deterministic paths instead of hanging the UI.
    return OpenAI(api_key=api_key(), timeout=timeout_s, max_retries=0)


def _gemini_model():
    import google.generativeai as genai  # type: ignore

    genai.configure(api_key=api_key())
    return genai.GenerativeModel(model_name())


def generate_json(prompt: str, timeout_s: float = 8) -> str | None:
    """One JSON-mode completion. Returns raw text (caller extracts the JSON) or None."""
    if not is_available():
        return None
    try:
        if provider() == "openai":
            client = _openai_client(timeout_s)
            resp = client.chat.completions.create(
                model=model_name(),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return (resp.choices[0].message.content or "").strip()
        model = _gemini_model()
        resp = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            request_options={"timeout": timeout_s},
        )
        return (getattr(resp, "text", "") or "").strip()
    except Exception as exc:
        logger.warning("generate_json failed (%s): %s", provider(), exc)
        return None


def generate_text(prompt: str, timeout_s: float = 20) -> str | None:
    """One plain-text completion. Returns text or None."""
    if not is_available():
        return None
    try:
        if provider() == "openai":
            client = _openai_client(timeout_s)
            resp = client.chat.completions.create(
                model=model_name(),
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip()
        model = _gemini_model()
        resp = model.generate_content(prompt, request_options={"timeout": timeout_s})
        return (getattr(resp, "text", "") or "").strip()
    except Exception as exc:
        logger.warning("generate_text failed (%s): %s", provider(), exc)
        return None


def ocr_image(image_bytes: bytes, mime_type: str, prompt: str, timeout_s: float = 30) -> str:
    """Vision transcription of one image. Returns '' on any failure."""
    if not image_bytes or not is_available():
        return ""
    try:
        if provider() == "openai":
            client = _openai_client(timeout_s)
            data_uri = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode()}"
            resp = client.chat.completions.create(
                model=model_name(),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
            )
            return (resp.choices[0].message.content or "").strip()
        model = _gemini_model()
        resp = model.generate_content([{"mime_type": mime_type, "data": image_bytes}, prompt])
        return (getattr(resp, "text", "") or "").strip()
    except Exception as exc:
        logger.warning("ocr_image failed (%s): %s", provider(), exc)
        return ""


_MIME_EXT = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/ogg": "ogg",
}


def transcribe_audio(
    audio_bytes: bytes, mime: str, prompt: str, lang: str = "en", timeout_s: float = 30
) -> str:
    """Verbatim speech-to-text. Returns '' on any failure.

    OpenAI path uses the dedicated transcription endpoint (Whisper) with a
    language hint; Gemini path sends an inline audio part with the prompt.
    """
    if not audio_bytes or not is_available():
        return ""
    try:
        if provider() == "openai":
            client = _openai_client(timeout_s)
            ext = _MIME_EXT.get((mime or "").split(";")[0].strip().lower(), "wav")
            resp = client.audio.transcriptions.create(
                model=os.environ.get("OPENAI_STT_MODEL", _DEFAULT_OPENAI_STT_MODEL),
                file=(f"voice.{ext}", io.BytesIO(audio_bytes)),
                language=lang if lang in ("en", "si", "ta") else "en",
            )
            return (getattr(resp, "text", "") or "").strip()
        model = _gemini_model()
        resp = model.generate_content([{"mime_type": mime, "data": audio_bytes}, prompt])
        return (getattr(resp, "text", "") or "").strip()
    except Exception as exc:
        logger.warning("transcribe_audio failed (%s): %s", provider(), exc)
        return ""


def pydantic_ai_model():
    """Model object for the Pydantic AI booking agent, or None when unavailable."""
    if not is_available():
        return None
    try:
        if provider() == "openai":
            from pydantic_ai.models.openai import OpenAIModel  # type: ignore
            from pydantic_ai.providers.openai import OpenAIProvider  # type: ignore

            return OpenAIModel(model_name(), provider=OpenAIProvider(api_key=api_key()))
        # Prefer GoogleModel (current pydantic-ai); fall back to deprecated GeminiModel
        # when an older/newer install only ships one of the two entry points.
        try:
            from pydantic_ai.models.google import GoogleModel  # type: ignore
            from pydantic_ai.providers.google import GoogleProvider  # type: ignore

            return GoogleModel(model_name(), provider=GoogleProvider(api_key=api_key()))
        except Exception as google_exc:
            logger.debug("GoogleModel unavailable (%s); trying GeminiModel", google_exc)
            from pydantic_ai.models.gemini import GeminiModel  # type: ignore
            from pydantic_ai.providers.google_gla import GoogleGLAProvider  # type: ignore

            return GeminiModel(model_name(), provider=GoogleGLAProvider(api_key=api_key()))
    except Exception as exc:
        logger.warning("pydantic_ai_model unavailable (%s): %s", provider(), exc)
        return None
