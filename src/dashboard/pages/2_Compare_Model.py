# =========================================
# ADVANCED MODEL COMPARISON DASHBOARD (FINAL)
# =========================================

import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.utils.api_client import call_inference


# =========================================
# HEADER (PAGE LEVEL ONLY)
# =========================================
st.subheader("🧠 Advanced Model Comparison")


# =========================================
# SIDEBAR
# =========================================
st.sidebar.header("⚙️ Controls")

models = st.sidebar.multiselect(
    "Select Models",
    ["xgboost", "isolationforest"],
    default=["xgboost", "isolationforest"],
    key="compare_models_select"
)

mode = st.sidebar.radio(
    "Mode",
    ["Generate Data", "Upload CSV"],
    key="compare_mode"
)


# =========================================
# SESSION STATE
# =========================================
if "compare_df" not in st.session_state:
    st.session_state.compare_df = None


# =========================================
# DATA INPUT
# =========================================
if mode == "Generate Data":

    from xgboost_ad.validator import generate_test_data

    hours = st.sidebar.slider("Hours", 24, 200, 48, key="compare_hours")
    anomaly_prob = st.sidebar.slider("Anomaly Probability", 0.0, 0.5, 0.2, key="compare_prob")

    if st.sidebar.button("Generate Data", key="compare_generate"):
        st.session_state.compare_df = generate_test_data(
            start_date=pd.Timestamp("2026-05-01"),
            hours=hours,
            anomaly_prob=anomaly_prob
        )

elif mode == "Upload CSV":

    file = st.sidebar.file_uploader("Upload CSV", key="compare_upload")

    if file:
        df = pd.read_csv(file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        st.session_state.compare_df = df


df = st.session_state.compare_df

if df is None:
    st.warning("Generate or upload data")
    st.stop()


# =========================================
# INPUT PREVIEW
# =========================================
st.subheader("📄 Input Data Preview")
st.dataframe(df.head(50), width="stretch")


# =========================================
# RUN ANALYSIS
# =========================================
if st.sidebar.button("Run Analysis", key="compare_run"):

    if not models:
        st.warning("Select at least one model")
        st.stop()

    with st.spinner("Running comparison..."):

        df_copy = df.copy()

        # Fix datetime serialization
        for col in df_copy.select_dtypes(include=["datetime64[ns]"]).columns:
            df_copy[col] = df_copy[col].astype(str)

        payload = {
            "models": models,
            "data": df_copy.to_dict(orient="records")
        }

        response = call_inference(payload)

        results = {
            m: pd.DataFrame(response["results"][m])
            for m in models
        }

        metadata = response["metadata"]

    # =========================================
    # KPI CARDS
    # =========================================
    st.subheader("📊 Model KPIs")

    cols = st.columns(len(models))

    for i, m in enumerate(models):

        res = results[m]
        total = len(res)
        alerts = (res["Status"] != "Normal ✅").sum()
        alert_pct = (alerts / total * 100) if total else 0

        cols[i].metric(
            m.upper(),
            alerts,
            f"{alert_pct:.2f}% | {metadata[m]['latency_ms']} ms"
        )

    st.markdown("---")

    # =========================================
    # MODEL METADATA
    # =========================================
    st.subheader("⚙️ Model Metadata")

    meta_df = pd.DataFrame(metadata).T
    st.dataframe(meta_df, width="stretch")

    # =========================================
    # OVERLAP ANALYSIS
    # =========================================
    st.subheader("🔗 Overlap & Agreement")

    if len(models) >= 2:

        m1, m2 = models[:2]

        df1 = results[m1]
        df2 = results[m2]

        merged = df1.copy()
        merged["a1"] = df1["Status"] != "Normal ✅"
        merged["a2"] = df2["Status"] != "Normal ✅"

        both = (merged["a1"] & merged["a2"]).sum()
        only_1 = (merged["a1"] & ~merged["a2"]).sum()
        only_2 = (~merged["a1"] & merged["a2"]).sum()
        none = (~merged["a1"] & ~merged["a2"]).sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Both 🚨", both)
        c2.metric(f"{m1} Only", only_1)
        c3.metric(f"{m2} Only", only_2)
        c4.metric("No Alert", none)

        overlap_df = pd.DataFrame({
            "Category": ["Both", m1, m2, "None"],
            "Count": [both, only_1, only_2, none]
        })

        fig = px.bar(overlap_df, x="Category", y="Count")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")

    # =========================================
    # TIME SERIES
    # =========================================
    st.subheader("📈 Alerts Over Time")

    ts_all = []

    for m in models:
        temp = results[m].copy()
        temp["Timestamp"] = pd.to_datetime(temp["Timestamp"])
        temp = temp[temp["Status"] != "Normal ✅"]

        g = temp.groupby("Timestamp").size().reset_index(name="alerts")
        g["model"] = m
        ts_all.append(g)

    if ts_all:
        ts_df = pd.concat(ts_all)
        fig = px.line(ts_df, x="Timestamp", y="alerts", color="model")
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")

    # =========================================
    # ROOT CAUSE
    # =========================================
    st.subheader("📊 Root Cause Comparison")

    cols = st.columns(len(models))

    for i, m in enumerate(models):
        alerts_df = results[m][results[m]["Status"] != "Normal ✅"]

        if not alerts_df.empty:
            rc = alerts_df["Root_Cause"].value_counts().reset_index()
            rc.columns = ["Root_Cause", "Count"]

            fig = px.bar(rc, x="Root_Cause", y="Count", title=m)
            cols[i].plotly_chart(fig, width="stretch")

    st.markdown("---")

    # =========================================
    # SEVERITY DISTRIBUTION
    # =========================================
    st.subheader("⚠️ Severity Distribution")

    sev_all = []

    for m in models:
        temp = results[m].copy()
        temp["model"] = m
        sev_all.append(temp)

    sev_df = pd.concat(sev_all)

    fig = px.histogram(
        sev_df,
        x="Severity",
        color="model",
        nbins=30,
        barmode="overlay"
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")

    # =========================================
    # AGREEMENT TABLE
    # =========================================
    st.subheader("🧾 Agreement Table")

    if len(models) >= 2:

        merged = results[models[0]][["Timestamp", "Command", "Status"]].copy()
        merged.columns = ["Timestamp", "Command", models[0]]

        for m in models[1:]:
            merged[m] = results[m]["Status"]

        merged["Agreement"] = merged[models].nunique(axis=1) == 1

        st.dataframe(merged.head(100), width="stretch")

    st.markdown("---")

    # =========================================
    # RAW DATA
    # =========================================
    with st.expander("📄 Raw Results"):
        for m in models:
            st.subheader(m.upper())
            st.dataframe(results[m].head(50), width="stretch")