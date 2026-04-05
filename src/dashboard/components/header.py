
import streamlit as st
import requests
from common.config_loader import load_main_config, get_api_config

cfg = load_main_config()
api_cfg = get_api_config(cfg)
API_URL = api_cfg.get("base_url")


def check_api():
    try:
        return requests.get(API_URL, timeout=2).status_code == 200
    except:
        return False


def render_header():

    st.markdown("""
    <style>
    .topbar {
        background: #0f172a;
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .logo {
        font-size: 22px;
        font-weight: 800;
        color: #38bdf8;
    }

    .title {
        font-size: 18px;
        font-weight: 600;
        color: white;
    }

    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        st.markdown('<div class="logo">S9S</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="title">EPP SLA Anomaly Detection</div>', unsafe_allow_html=True)

    with col3:
        if check_api():
            st.success("API OK")
        else:
            st.error("API DOWN")

    st.divider()