import streamlit as st

st.set_page_config(layout="wide")

st.title("🚨 Anomaly Detection")

page = st.sidebar.selectbox(
    "Select View",
    ["Single Model", "Compare Models"]
)

if page == "Single Model":
    import dashboard.pages.single_model

elif page == "Compare Models":
    import dashboard.pages.compare_models 


#================================================
# streamlit run dashboard/app.py
#=================================================