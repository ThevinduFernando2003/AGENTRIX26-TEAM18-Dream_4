"""Streamlit auth: bcrypt-hashed passwords, session-based login."""

from __future__ import annotations

from typing import Optional

import streamlit as st
from passlib.context import CryptContext

from ..db.db import get_conn

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
            _pwd.hash(password),
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
    if not _pwd.verify(password, row["password_hash"]):
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


def logout() -> None:
    for k in ("user_id", "user_cache", "geo", "manual_geo"):
        st.session_state.pop(k, None)


def render_auth_gate() -> Optional[dict]:
    """Renders login/signup UI if not logged in. Returns the user dict or None."""
    user = current_user()
    if user:
        return user

    st.title("MedBridge AI")
    st.caption("Multi-agent healthcare navigator — demo build (Team Dream_4)")

    tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                uid = login(u.strip(), p)
                if uid is None:
                    st.error("Invalid username or password.")
                else:
                    st.session_state["user_id"] = uid
                    st.rerun()

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            u = st.text_input("Username", key="su_user")
            p = st.text_input("Password (min 6 chars)", type="password", key="su_pw")
            full_name = st.text_input("Full name", key="su_name")
            age = st.number_input("Age", min_value=0, max_value=120, value=30, key="su_age")
            gender = st.selectbox("Gender", ["", "M", "F", "Other"], key="su_gender")
            lang = st.selectbox("Preferred language", ["en", "si", "ta"], key="su_lang")
            fc_name = st.text_input("Family contact name (for emergency push)", key="su_fcn")
            fc_phone = st.text_input("Family contact phone", key="su_fcp")
            if st.form_submit_button("Create account"):
                ok, msg = signup(
                    u.strip(), p, full_name, int(age), gender, lang, fc_name, fc_phone
                )
                (st.success if ok else st.error)(msg)

    return None
