# =========================================
# ADVANCED MODEL COMPARISON DASHBOARD (UPDATED)
# =========================================

import streamlit as st
import pandas as pd
import requests
import plotly.express as px

API_URL = "http://localhost:8000/compare"

st.set_page_config(layout="wide")
st.title("🧠 Advanced Model Comparison")
st.caption("Deep analysis of anomaly detection models")

# =========================================
# SIDEBAR
# =========================================
st.sidebar.header("⚙️ Controls")

models = st.sidebar.multiselect(
    "Select Models",
    ["xgboost", "isolationforest"],
    default=["xgboost", "isolationforest"]
)

mode = st.sidebar.radio("Mode", ["Generate Data", "Upload CSV"])

# =========================================
# DATA INPUT
# =========================================


if "df" not in st.session_state:
    st.session_state.df = None

if mode == "Generate Data":

    from xgboost_ad.validator import generate_test_data

    hours = st.sidebar.slider("Hours", 24, 200, 48)
    anomaly_prob = st.sidebar.slider("Anomaly Probability", 0.0, 0.5, 0.2)

    if st.sidebar.button("Generate Data"):
        st.session_state.df = generate_test_data(
            start_date=pd.Timestamp("2026-05-01"),
            hours=hours,
            anomaly_prob=anomaly_prob
        )
        st.subheader("📄 Input Data Preview")
        st.dataframe(st.session_state.df.head(50), width="stretch")

elif mode == "Upload CSV":

    file = st.sidebar.file_uploader("Upload CSV")
    if file:
        df = pd.read_csv(file)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        st.session_state.df = df
    

# stop if no data
df = st.session_state.df

if df is None:
    st.warning("Generate or upload data")
    st.stop()


# =========================================
# RUN ANALYSIS
# =========================================
if st.sidebar.button("Run Analysis"):

    # ✅ Fix datetime serialization
    df_copy = df.copy()
    for col in df_copy.select_dtypes(include=["datetime64[ns]"]).columns:
        df_copy[col] = df_copy[col].astype(str)

    payload = {
        "models": models,
        "data": df_copy.to_dict(orient="records")
    }

    response = requests.post(API_URL, json=payload).json()
    results = {m: pd.DataFrame(response[m]) for m in models}

    # =========================================
    # KPI CARDS
    # =========================================
    st.subheader("📊 Model KPIs")

    cols = st.columns(len(models))

    for i, m in enumerate(models):
        res = results[m]
        alerts = (res["Status"] != "Normal ✅").sum()
        total = len(res)

        cols[i].metric(
            m,
            f"{alerts}",
            f"{round(alerts/total*100,2)}% alert rate"
        )

    st.markdown("---")

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
            "Category": ["Both", f"{m1}", f"{m2}", "None"],
            "Count": [both, only_1, only_2, none]
        })

        fig = px.bar(overlap_df, x="Category", y="Count", title="Overlap Distribution")
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
            st.subheader(m)
            st.dataframe(results[m].head(50), width="stretch")
