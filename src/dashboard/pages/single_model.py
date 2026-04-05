# =========================================
# SINGLE MODEL DASHBOARD (UPDATED)
# =========================================

import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils.api_client import call_inference

st.set_page_config(page_title="EPP SLA Hourly Anomaly Dashboard", layout="wide")

# =========================================
# HEADER
# =========================================
st.title("🚨 EPP SLA Hourly Anomaly Detection Dashboard")
st.caption("Single Model Inference & Analysis")

# =========================================
# SIDEBAR
# =========================================
st.sidebar.header("⚙️ Controls")

model = st.sidebar.selectbox(
    "Select Model",
    ["xgboost", "isolationforest"]
)

mode = st.sidebar.radio("Mode", ["Generate Data", "Upload CSV"])

# Filters
st.sidebar.subheader("🔍 Filters")
selected_command = st.sidebar.multiselect(
    "Command",
    ["CHECK-DOMAIN", "ADD-DOMAIN", "MOD-DOMAIN", "DEL-DOMAIN"]
)

selected_status = st.sidebar.multiselect(
    "Status",
    ["Normal ✅", "LOW ⚠️", "MEDIUM ⚠️", "CRITICAL 🚨"]
)

# =========================================
# DATA INPUT
# =========================================
df = None

if mode == "Generate Data":

    from xgboost_ad.validator import generate_test_data

    hours = st.sidebar.slider("Hours", 24, 200, 48)
    anomaly_prob = st.sidebar.slider("Anomaly Probability", 0.0, 0.5, 0.2)

    if st.sidebar.button("Generate Data"):
        df = generate_test_data(
            start_date=pd.Timestamp("2026-05-01"),
            hours=hours,
            anomaly_prob=anomaly_prob
        )

elif mode == "Upload CSV":

    file = st.sidebar.file_uploader("Upload CSV")

    if file:
        df = pd.read_csv(file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

# =========================================
# RUN INFERENCE
# =========================================
if df is not None:

    with st.spinner("Running inference..."):

        df_copy = df.copy()

        # Fix datetime serialization
        for col in df_copy.select_dtypes(include=["datetime64[ns]"]).columns:
            df_copy[col] = df_copy[col].astype(str)

        payload = {
            "models": [model],   # ✅ unified format
            "data": df_copy.to_dict(orient="records")
        }

        response = call_inference(payload)

        results = pd.DataFrame(response["results"][model])
        meta = response["metadata"][model]

    # =========================================
    # FILTERS
    # =========================================
    if selected_command:
        results = results[results["Command"].isin(selected_command)]

    if selected_status:
        results = results[results["Status"].isin(selected_status)]

    # =========================================
    # KPI CARDS
    # =========================================
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Model", model.upper())
    c2.metric("Total", len(results))

    alerts = (results["Status"] != "Normal ✅").sum()
    c3.metric("Alerts", alerts)

    c4.metric("Alert %", f"{alerts/len(results)*100:.2f}%")
    c5.metric("Latency (ms)", meta["latency_ms"])

    st.markdown("---")

    # =========================================
    # TIME SERIES
    # =========================================
    st.subheader("📈 Alerts Over Time")

    ts = results.copy()
    ts["Timestamp"] = pd.to_datetime(ts["Timestamp"])

    ts = (
        ts[ts["Status"] != "Normal ✅"]
        .groupby("Timestamp")
        .size()
        .reset_index(name="alerts")
    )

    if not ts.empty:
        fig = px.line(ts, x="Timestamp", y="alerts", markers=True)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No alerts detected")

    # =========================================
    # ROOT CAUSE
    # =========================================
    st.subheader("📊 Root Cause Distribution")

    alerts_df = results[results["Status"] != "Normal ✅"]

    if not alerts_df.empty:
        rc = alerts_df["Root_Cause"].value_counts().reset_index()
        rc.columns = ["Root_Cause", "Count"]

        fig = px.bar(rc, x="Root_Cause", y="Count")
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No anomalies")

    # =========================================
    # SEVERITY DISTRIBUTION
    # =========================================
    st.subheader("⚠️ Severity Distribution")

    if not alerts_df.empty:
        fig = px.histogram(alerts_df, x="Severity", nbins=30)
        st.plotly_chart(fig, width="stretch")

    # =========================================
    # COMMAND DISTRIBUTION
    # =========================================
    st.subheader("🧩 Alerts by Command")

    if not alerts_df.empty:
        cmd_df = alerts_df["Command"].value_counts().reset_index()
        cmd_df.columns = ["Command", "Count"]

        fig = px.bar(cmd_df, x="Command", y="Count")
        st.plotly_chart(fig, width="stretch")

    # =========================================
    # ALERT TABLE
    # =========================================
    st.subheader("🚨 Alerts")

    st.dataframe(
        alerts_df.sort_values("Severity", ascending=False),
        width="stretch"
    )

    # =========================================
    # RAW DATA
    # =========================================
    with st.expander("📄 Raw Input Data"):
        st.dataframe(df.head(100), width="stretch")

    with st.expander("📄 Full Results"):
        st.dataframe(results.head(100), width="stretch")