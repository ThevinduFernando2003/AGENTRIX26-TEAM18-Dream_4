"""Shared helpers for the Streamlit UI panels.

Lifted out of the old monolithic ``app.py`` so every panel module reuses the same
geolocation, language, and disclaimer logic instead of duplicating it.
"""

from __future__ import annotations

import streamlit as st

from ..i18n.translate import t


LANGUAGE_SHORT_LABELS = {
    "en": "E",
    "si": "සි",
    "ta": "த",
}


def render_branding_styles() -> None:
    """Inject CSS only for the top banner."""
    st.markdown(
        """
        <style>
        .medbridge-banner {
            background: linear-gradient(135deg, #0f172a 0%, #111827 100%);
            color: #f8fafc;
            border-radius: 14px;
            padding: 1.4rem 1.6rem;
            margin: 0 0 1rem 0;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
        }
        .medbridge-banner__title {
            font-size: 2.2rem;
            font-weight: 800;
            line-height: 1.15;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .medbridge-banner__subtitle {
            margin-top: 0.55rem;
            color: rgba(226, 232, 240, 0.9);
            font-size: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_banner(lang: str) -> None:
    """Render the shared branded top banner."""
    st.markdown(
        f"""
        <div class="medbridge-banner">
            <div class="medbridge-banner__title">{t('app.title', lang)}</div>
            <div class="medbridge-banner__subtitle">{t('app.caption', lang)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_rights_banner(lang: str) -> None:
    """Render the rights notice at the bottom of the login / sign-up page."""
    st.divider()
    st.caption(f"© {t('app.rights', lang)}", )


def render_sidebar_rights_banner(lang: str) -> None:
    """Render the rights notice at the bottom of the sidebar (inside st.sidebar context)."""
    st.caption(f"© {t('app.rights', lang)}")


def language_short_label(lang: str) -> str:
    """Professional short label used in language UI controls."""
    return LANGUAGE_SHORT_LABELS.get(lang, LANGUAGE_SHORT_LABELS["en"])


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
