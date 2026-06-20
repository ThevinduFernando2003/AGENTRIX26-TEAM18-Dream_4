"""Streamlit auth: bcrypt-hashed passwords, session-based login."""

from __future__ import annotations

from typing import Optional

import bcrypt
import streamlit as st

from ..db.db import get_conn
from ..i18n.translate import t


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


def current_user() -> Optional[dict]:
    uid = st.session_state.get("user_id")
    if not uid:
        return None
    cached = st.session_state.get("user_cache")
    if cached and cached.get("user_id") == uid:
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


def render_auth_gate() -> Optional[dict]:
    """Renders login/signup UI if not logged in. Returns the user dict or None."""
    user = current_user()
    if user:
        return user

    # Auth screen runs before we know the user's preference — show English
    # primary and (Si/Ta) variants of the key labels for accessibility. Inside
    # the app proper, language flips to the user's choice.
    L = "en"

    st.title(t("auth.title", L))
    st.caption(t("auth.tagline", L))

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
                    st.rerun()

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            u = st.text_input(t("auth.username", L), key="su_user")
            p = st.text_input(t("auth.password", L) + " (min 6 chars)", type="password", key="su_pw")
            full_name = st.text_input(t("auth.fullname", L), key="su_name")
            age = st.number_input(t("auth.age", L), min_value=0, max_value=120, value=30, key="su_age")
            gender = st.selectbox(t("auth.gender", L), ["", "M", "F", "Other"], key="su_gender")
            lang = st.selectbox(t("auth.pref_lang", L), ["en", "si", "ta"], key="su_lang")
            fc_name = st.text_input(t("auth.family_name", L), key="su_fcn")
            fc_phone = st.text_input(t("auth.family_phone", L), key="su_fcp")
            if st.form_submit_button(t("auth.signup_btn", L)):
                ok, msg = signup(
                    u.strip(), p, full_name, int(age), gender, lang, fc_name, fc_phone
                )
                (st.success if ok else st.error)(msg)

    return None
