"""Shared helpers for the Streamlit UI panels.

Lifted out of the old monolithic ``app.py`` so every panel module reuses the same
geolocation, language, and disclaimer logic instead of duplicating it.
"""

from __future__ import annotations

import streamlit as st

from ..i18n.translate import t


def get_geo() -> tuple[float | None, float | None]:
    """Resolve the user's coordinates from the geolocation widget or manual entry."""
    geo = st.session_state.get("geo") or {}
    lat = geo.get("latitude") or geo.get("lat")
    lng = geo.get("longitude") or geo.get("lng")
    manual = st.session_state.get("manual_geo") or {}
    return (lat or manual.get("lat"), lng or manual.get("lng"))


def lang_of(user: dict | None) -> str:
    """Preferred language for a user dict, defaulting to English."""
    u = user or {}
    return u.get("preferred_language", "en") or "en"


def disclaimer(lang: str) -> str:
    """The standard footer disclaimer, appended by the UI (never by the LLM)."""
    return t("disclaimer.footer", lang)
