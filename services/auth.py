"""Simple authentication for Streamlit app."""

import os
import hashlib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Default password hash (sha256 of "whisky")
# Change WHISKY_PASSWORD in .env to use a different password
DEFAULT_PASSWORD_HASH = hashlib.sha256("whisky".encode()).hexdigest()


def get_password_hash():
    """Get the configured password hash."""
    password = os.getenv("WHISKY_PASSWORD")
    if password:
        return hashlib.sha256(password.encode()).hexdigest()
    return DEFAULT_PASSWORD_HASH


def check_password(password: str) -> bool:
    """Check if the provided password is correct."""
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == get_password_hash()


def is_authenticated() -> bool:
    """Check if the user is authenticated."""
    return st.session_state.get("authenticated", False)


def logout():
    """Log out the current user."""
    st.session_state.authenticated = False


def require_auth():
    """
    Require authentication to access the page.
    Call this at the beginning of each page.
    Returns True if authenticated, False otherwise.
    """
    # Check if already authenticated
    if is_authenticated():
        return True

    # Show login form
    st.title("🔐 Anmeldung erforderlich")
    st.write("Bitte melde dich an, um auf die Whisky-Sammlung zuzugreifen.")

    with st.form("login_form"):
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Anmelden", type="primary")

        if submitted:
            if check_password(password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Falsches Passwort!")

    st.caption("Standard-Passwort: `whisky` (kann via WHISKY_PASSWORD in .env geändert werden)")

    return False


def show_logout_button():
    """Show a logout button in the sidebar."""
    if is_authenticated():
        with st.sidebar:
            st.divider()
            if st.button("🚪 Abmelden", use_container_width=True):
                logout()
                st.rerun()
