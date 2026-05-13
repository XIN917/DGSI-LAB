"""3D Printer Production Simulator — Streamlit dashboard entry point."""
import os
import sys

# Ensure project root is in sys.path for module discovery
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import requests
import streamlit as st

from dashboard.style import inject_styles
from dashboard.components.header import render_header
from dashboard.components.inventory_panel import render_inventory_panel
from dashboard.components.orders_panel import render_orders_panel
from dashboard.components.actions_panel import render_actions_panel
from dashboard.components.event_log import render_event_log

API_BASE = "http://localhost:8000"


def _api(method: str, path: str, **kwargs) -> requests.Response:
    token = st.session_state.get("token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.request(method, f"{API_BASE}{path}", headers=headers, timeout=10, **kwargs)


def get(path: str, **kwargs) -> dict:
    return _api("GET", path, **kwargs).json()


def post(path: str, **kwargs) -> dict | None:
    r = _api("POST", path, **kwargs)
    if not r.ok:
        st.error(f"API {r.status_code}: {r.json().get('detail', r.text)}")
        return None
    return r.json()


def login_page() -> None:
    inject_styles()
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        # Header Box (Sized to fit text precisely)
        st.markdown(
            '<div style="text-align:center; margin-top:80px; margin-bottom: 24px;">'
            '<div style="display:inline-block; padding:16px 32px; background:#1E293B;'
            'border:1px solid #334155; border-radius:10px; width: auto;">'
            '<div style="font-size:13px;font-weight:600;letter-spacing:0.06em;'
            'color:#F8FAFC;margin-bottom:4px; white-space: nowrap;">DGSI PRODUCTION SIMULATOR</div>'
            '<div style="font-size:10px;color:#475569;letter-spacing:0.04em;'
            'white-space: nowrap;">3D Printer Factory Operations</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            st.markdown(
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                'text-transform:uppercase;color:#64748B;margin-bottom:8px">Username</div>',
                unsafe_allow_html=True,
            )
            username = st.text_input("Username", value="admin", label_visibility="collapsed")
            st.markdown(
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                'text-transform:uppercase;color:#64748B;margin:12px 0 8px">Password</div>',
                unsafe_allow_html=True,
            )
            password = st.text_input("Password", type="password", label_visibility="collapsed")
            st.write("")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            try:
                r = requests.post(
                    f"{API_BASE}/api/auth/login",
                    data={"username": username, "password": password},
                    timeout=5,
                )
                if r.ok:
                    data = r.json()
                    st.session_state["token"] = data["access_token"]
                    st.session_state["user"] = data["user"]
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to API server. Please ensure the backend is running on port 8000.")

        st.markdown("</div>", unsafe_allow_html=True)


def main_dashboard() -> None:
    inject_styles()
    user = st.session_state.get("user", {})

    render_header(get, post, user)
    st.divider()

    left, center, right = st.columns([1, 1.2, 0.8])
    with left:
        render_inventory_panel(get, post)
    with center:
        render_orders_panel(get, post)
    with right:
        render_actions_panel(get, post)

    st.divider()
    render_event_log(get)


# ── Entry point ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DGSI Production Simulator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "token" not in st.session_state:
    login_page()
else:
    main_dashboard()
