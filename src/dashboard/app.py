import streamlit as st
from dashboard.components.header import render_header

st.set_page_config(layout="wide")

# Hide app.py from sidebar
st.markdown("""
<style>
[data-testid="stSidebarNav"] ul li:first-child {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# Shared header
render_header()

# Default landing content
st.subheader("📊 Welcome")

st.info("Select a dashboard from the sidebar →")

st.markdown("""
### Available Dashboards

- 📊 **Single Model** → Analyze one model  
- 🧠 **Compare Models** → Compare multiple models  

---
""")
