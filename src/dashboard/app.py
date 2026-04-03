# =========================================
# MODULE: Rich Streamlit Dashboard
# =========================================

import streamlit as st
import pandas as pd
import plotly.express as px

from anomaly_detection.inference.inference import run_inference
from anomaly_detection.validation.validator import generate_test_data

st.set_page_config(page_title="Anomaly Dashboard", layout="wide")

# =========================================
# HEADER
# =========================================
st.title("🚨 Anomaly Detection Dashboard")
st.caption("Real-time anomaly monitoring system")

# =========================================
# SIDEBAR
# =========================================
st.sidebar.header("⚙️ Controls")

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
if mode == "Generate Data":

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
# PROCESS DATA
# =========================================
if "df" in locals():

    results = run_inference(df)

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
    total = len(results)
    alerts = (results["Status"] != "Normal ✅").sum()
    alert_rate = alerts / total if total else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Records", total)
    col2.metric("Alerts", alerts)
    col3.metric("Alert Rate", f"{alert_rate*100:.2f}%")

    st.markdown("---")

    # =========================================
    # TIME SERIES
    # =========================================
    st.subheader("📈 Alerts Over Time")

    ts_df = results.copy()
    ts_df["Timestamp"] = pd.to_datetime(ts_df["Timestamp"])

    ts_chart = (
        ts_df[ts_df["Status"] != "Normal ✅"]
        .groupby("Timestamp")
        .size()
        .reset_index(name="alerts")
    )

    if not ts_chart.empty:
        fig = px.line(ts_chart, x="Timestamp", y="alerts", title="Alerts Timeline")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alerts to display")

    # =========================================
    # ROOT CAUSE DISTRIBUTION
    # =========================================
    st.subheader("📊 Root Cause Distribution")

    alerts_df = results[results["Status"] != "Normal ✅"]

    if not alerts_df.empty:
        fig = px.bar(
            alerts_df["Root_Cause"].value_counts().reset_index(),
            x="index",
            y="Root_Cause",
            labels={"index": "Metric", "Root_Cause": "Count"},
            title="Anomalies by Metric"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No anomalies detected")

    # =========================================
    # SEVERITY DISTRIBUTION
    # =========================================
    st.subheader("⚠️ Severity Distribution")

    if not alerts_df.empty:
        fig = px.pie(
            alerts_df,
            names="Status",
            title="Severity Breakdown"
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================
    # ALERTS TABLE
    # =========================================
    st.subheader("🚨 Alerts")

    st.dataframe(alerts_df.sort_values("Severity", ascending=False), use_container_width=True)

    # =========================================
    # RAW DATA
    # =========================================
    with st.expander("📄 View Raw Data"):
        st.dataframe(df.head(100), use_container_width=True)
