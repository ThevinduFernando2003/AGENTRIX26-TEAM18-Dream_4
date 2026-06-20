"""Streamlit auth: bcrypt-hashed passwords, session-based login."""

from __future__ import annotations

from typing import Optional

import bcrypt
import streamlit as st

from ..db.db import get_conn
from ..i18n.translate import t
from .common import language_short_label, render_auth_rights_banner, render_top_banner


def _hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _verify_pw(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def signup(
    username: str,
    password: str,
    full_name: str = "",
    age: Optional[int] = None,
    gender: str = "",
    preferred_language: str = "en",
    family_contact_name: str = "",
    family_contact_phone: str = "",
) -> tuple[bool, str]:
    if not username or not password:
        return False, "Username and password are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    conn = get_conn()
    if conn.execute("SELECT 1 FROM User WHERE username = ?", (username,)).fetchone():
        return False, "That username is already taken."

    conn.execute(
        """INSERT INTO User(username, password_hash, full_name, age, gender,
                            preferred_language, family_contact_name, family_contact_phone)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            username,
            _hash_pw(password),
            full_name or None,
            age,
            gender or None,
            preferred_language,
            family_contact_name or None,
            family_contact_phone or None,
        ),
    )
    conn.commit()
    return True, "Account created. Please log in."


def login(username: str, password: str) -> Optional[int]:
    conn = get_conn()
    row = conn.execute(
        "SELECT user_id, password_hash FROM User WHERE username = ?", (username,)
    ).fetchone()
    if not row:
        return None
    if not _verify_pw(password, row["password_hash"]):
        return None
    return int(row["user_id"])


def load_user(user_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute(
        """SELECT user_id, username, full_name, age, gender, preferred_language,
                  family_contact_name, family_contact_phone
           FROM User WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def update_preferred_language(user_id: int, lang: str) -> None:
    """Persist a new preferred_language for the given user."""
    conn = get_conn()
    conn.execute(
        "UPDATE User SET preferred_language = ? WHERE user_id = ?",
        (lang, user_id),
    )
    conn.commit()


def invalidate_user_cache() -> None:
    """Drop the cached user dict so the next ``current_user()`` reloads from DB.

    Call this after any write to the current user's ``User`` row (e.g. a profile
    or preferred-language update). Without it, ``current_user()`` keeps serving a
    stale dict for the whole session because the cache is keyed only on user_id.
    """
    st.session_state.pop("user_cache", None)


def _restore_user_from_url() -> None:
    """Recover ``user_id`` from ``?uid=`` so a browser refresh stays logged in.

    Streamlit's ``session_state`` is wiped on hard refresh — without a URL or
    cookie backup, every F5 drops the user to the login screen. We store
    ``uid`` in ``st.query_params`` at login time and read it back here. The
    value isn't signed, so this is "remember me" not "auth" — fine for the
    demo's seeded mock data, not OK for real PHI.
    """
    if st.session_state.get("user_id"):
        return
    raw = st.query_params.get("uid")
    if not raw:
        return
    try:
        uid = int(raw)
    except (TypeError, ValueError):
        return
    if load_user(uid) is None:
        # Stale / tampered URL — drop it instead of crashing.
        try:
            del st.query_params["uid"]
        except KeyError:
            pass
        return
    st.session_state["user_id"] = uid


def current_user(force_reload: bool = False) -> Optional[dict]:
    _restore_user_from_url()
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    # Defence-in-depth: drop a stale ``user_cache`` from a previous user that
    # somehow survived a partial logout.
    cached = st.session_state.get("user_cache")
    if cached and cached.get("user_id") != uid:
        st.session_state.pop("user_cache", None)
        cached = None
    if not force_reload and cached:
        return cached
    u = load_user(uid)
    if u:
        st.session_state["user_cache"] = u
    return u


# Process-scoped session keys that must survive logout (not user-scoped).
# `_db_inited` controls whether init_db() has run for this Streamlit
# process; clearing it would re-seed on every logout.
_PROCESS_SCOPED_KEYS = {"_db_inited"}


def logout() -> None:
    """Wipe every user-scoped key in session_state on logout.

    Whitelist-based: clears everything except keys in
    _PROCESS_SCOPED_KEYS. New panels/toggles added by teammates are
    cleared automatically — no maintenance burden on each addition.
    """
    for k in list(st.session_state.keys()):
        if k not in _PROCESS_SCOPED_KEYS:
            del st.session_state[k]
    # Drop the ``?uid=`` remember-me marker so the next login isn't shadowed
    # by the previous user's URL.
    try:
        st.query_params.clear()
    except Exception:
        # Older Streamlit builds may not support clear(); fall back to del.
        try:
            del st.query_params["uid"]
        except KeyError:
            pass


def render_auth_gate() -> Optional[dict]:
    """Renders login/signup UI if not logged in. Returns the user dict or None."""
    user = current_user()
    if user:
        return user

    # Auth screen runs before we know the user's preference — show English
    # primary and (Si/Ta) variants of the key labels for accessibility. Inside
    # the app proper, language flips to the user's choice.
    L = "en"

    render_top_banner(L)

    tab_login, tab_signup = st.tabs([t("auth.tab.login", L), t("auth.tab.signup", L)])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input(t("auth.username", L))
            p = st.text_input(t("auth.password", L), type="password")
            if st.form_submit_button(t("auth.login_btn", L)):
                uid = login(u.strip(), p)
                if uid is None:
                    st.error(t("auth.invalid", L))
                else:
                    st.session_state["user_id"] = uid
                    # Persist across browser refresh — see _restore_user_from_url.
                    st.query_params["uid"] = str(uid)
                    st.rerun()

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            u = st.text_input(t("auth.username", L), key="su_user")
            p = st.text_input(t("auth.password", L) + " (min 6 chars)", type="password", key="su_pw")
            full_name = st.text_input(t("auth.fullname", L), key="su_name")
            age = st.number_input(t("auth.age", L), min_value=0, max_value=120, value=30, key="su_age")
            gender = st.selectbox(t("auth.gender", L), ["", "M", "F", "Other"], key="su_gender")
            lang = st.selectbox(
                t("auth.pref_lang", L),
                ["en", "si", "ta"],
                key="su_lang",
                format_func=language_short_label,
            )
            fc_name = st.text_input(t("auth.family_name", L), key="su_fcn")
            fc_phone = st.text_input(t("auth.family_phone", L), key="su_fcp")
            if st.form_submit_button(t("auth.signup_btn", L)):
                ok, msg = signup(
                    u.strip(), p, full_name, int(age), gender, lang, fc_name, fc_phone
                )
                (st.success if ok else st.error)(msg)

    render_auth_rights_banner(L)
    return None
