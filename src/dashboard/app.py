import streamlit as st

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    layout="wide",
    page_title="EPP SLA Anomaly Detection"
)

# =========================================
# S9S ANIMATED LOGO (TOP LEFT)
# =========================================
st.markdown("""
<style>
.s9s-container {
    position: fixed;
    top: 12px;
    left: 20px;
    z-index: 9999;
    font-size: 28px;
    font-weight: 800;
    font-family: 'Segoe UI', sans-serif;
    letter-spacing: 2px;
}

/* Simple, reliable animation */
.s9s-text {
    color: #00c6ff;
    animation: glow 1.5s ease-in-out infinite alternate;
}

/* Glow animation (Streamlit-safe) */
@keyframes glow {
    from {
        opacity: 0.6;
        transform: scale(1);
    }
    to {
        opacity: 1;
        transform: scale(1.1);
    }
}
</style>

<div class="s9s-container">
    <div class="s9s-text">S9S</div>
</div>
""", unsafe_allow_html=True)

# =========================================
# HEADER
# =========================================
st.title("🚨 Anomaly Detection")
st.caption("EPP SLA Monitoring & Multi-Model Analysis")

st.markdown("---")

# =========================================
# SIDEBAR NAVIGATION
# =========================================
st.sidebar.header("📊 Navigation")

page = st.sidebar.radio(
    "Select View",
    ["Single Model", "Compare Models"]
)

# =========================================
# ROUTING
# =========================================
if page == "Single Model":
    import dashboard.pages.single_model

elif page == "Compare Models":
    import dashboard.pages.compare_models 

#================================================
# streamlit run dashboard/app.py
#=================================================