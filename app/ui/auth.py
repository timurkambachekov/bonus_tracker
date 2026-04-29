import streamlit as st

from app.ui.api_client import load_app_user, touch_app_user_login


def build_app_user(user):
    email = (getattr(user, "email", None) or "").strip().lower()
    if not email:
        return None

    app_user = load_app_user(email)
    if app_user and not app_user.get("full_name"):
        app_user["full_name"] = getattr(user, "name", None)
    return app_user


def require_login():
    auth = st.secrets.get("auth", {})
    required_auth_keys = {
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    }
    if not required_auth_keys.issubset(auth.keys()):
        st.title("Bonus Tracker")
        st.error("Streamlit authentication is not configured.")
        st.stop()

    user = st.user if hasattr(st, "user") else st.experimental_user
    if not getattr(user, "is_logged_in", False):
        st.title("Bonus Tracker")
        st.write("Sign in to access the app.")
        if st.button("Log in"):
            st.login()
        st.stop()

    email = (getattr(user, "email", None) or "").strip().lower()
    app_user = build_app_user(user)
    if not app_user:
        st.error("Your account is authenticated but not provisioned for this app.")
        if email:
            st.code(f"Authenticated email: {email}")
        st.caption("Ask an admin to add your email and club access.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    if not app_user["is_admin"] and not app_user["club_ids"]:
        st.error("Your account has no club access assigned.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    touch_app_user_login(app_user["id"])
    return app_user


def render_user_session(user):
    email = user.get("email")
    name = user.get("full_name")
    role = user.get("role")
        
    st.sidebar.write(name)
    st.sidebar.caption(email)
    st.sidebar.caption(role)
    
    if st.sidebar.button("Log out"):
        st.logout()
