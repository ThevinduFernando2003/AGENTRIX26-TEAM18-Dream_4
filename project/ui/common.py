"""Shared helpers for the Streamlit UI panels.

Lifted out of the old monolithic ``app.py`` so every panel module reuses the same
geolocation, language, and disclaimer logic instead of duplicating it.
"""

from __future__ import annotations

import math

import streamlit as st

from ..i18n.translate import t


LANGUAGE_SHORT_LABELS = {
    "en": "E",
    "si": "සි",
    "ta": "த",
}

# Approximate centres of major Sri Lankan cities. Used to (a) let the user pick a
# city instead of typing raw lat/long, and (b) show the nearest city label instead
# of bare coordinates. Distance maths still uses the coordinates under the hood.
SRI_LANKA_CITIES: dict[str, tuple[float, float]] = {
    "Colombo": (6.9271, 79.8612),
    "Dehiwala-Mount Lavinia": (6.8409, 79.8653),
    "Moratuwa": (6.7730, 79.8816),
    "Sri Jayawardenepura Kotte": (6.8880, 79.9180),
    "Negombo": (7.2083, 79.8358),
    "Gampaha": (7.0917, 79.9990),
    "Kalutara": (6.5854, 79.9607),
    "Kandy": (7.2906, 80.6337),
    "Galle": (6.0535, 80.2210),
    "Matara": (5.9485, 80.5353),
    "Kurunegala": (7.4863, 80.3623),
    "Anuradhapura": (8.3114, 80.4037),
    "Ratnapura": (6.6828, 80.3992),
    "Badulla": (6.9934, 81.0550),
    "Batticaloa": (7.7102, 81.6924),
    "Trincomalee": (8.5874, 81.2152),
    "Jaffna": (9.6615, 80.0255),
    "Nuwara Eliya": (6.9497, 80.7891),
}


def nearest_city(lat: float, lng: float) -> str:
    """Return the name of the closest known city to a coordinate (great-circle)."""
    def _dist(c: tuple[float, float]) -> float:
        (la, lo) = c
        p1, p2 = math.radians(lat), math.radians(la)
        dp, dl = math.radians(la - lat), math.radians(lo - lng)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * 6371.0 * math.asin(math.sqrt(a))

    return min(SRI_LANKA_CITIES, key=lambda name: _dist(SRI_LANKA_CITIES[name]))


def render_branding_styles() -> None:
    """Inject CSS for the branded top banner + a few calm clinical layout tweaks."""
    st.markdown(
        """
        <style>
        .medbridge-banner {
            background: linear-gradient(135deg, #0f766e 0%, #0d9488 55%, #14b8a6 100%);
            color: #f8fafc;
            border-radius: 16px;
            padding: 1.5rem 1.75rem;
            margin: 0 0 1.25rem 0;
            box-shadow: 0 12px 30px rgba(13, 148, 136, 0.22);
        }
        .medbridge-banner__row { display: flex; align-items: center; gap: 0.9rem; }
        .medbridge-banner__logo {
            font-size: 2rem; line-height: 1;
            background: rgba(255, 255, 255, 0.16);
            border-radius: 12px; padding: 0.5rem 0.65rem;
        }
        .medbridge-banner__title {
            font-size: 2rem; font-weight: 800; line-height: 1.12; margin: 0;
            letter-spacing: -0.02em;
        }
        .medbridge-banner__subtitle {
            margin-top: 0.3rem; color: rgba(240, 253, 250, 0.92); font-size: 1rem;
        }
        /* Slightly rounder dataframes/tables for a tidier card feel. */
        [data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: 10px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_banner(lang: str) -> None:
    """Render the shared branded top banner."""
    st.markdown(
        f"""
        <div class="medbridge-banner">
          <div class="medbridge-banner__row">
            <div class="medbridge-banner__logo">🩺</div>
            <div>
              <div class="medbridge-banner__title">{t('app.title', lang)}</div>
              <div class="medbridge-banner__subtitle">{t('app.caption', lang)}</div>
            </div>
          </div>
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
