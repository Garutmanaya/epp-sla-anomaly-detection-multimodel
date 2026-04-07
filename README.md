# 🚨 EPP SLA Anomaly Detection (Multi-Model)

## 🎯 Goal

Identify **deviations in hourly aggregated EPP SLA metrics**, including **minor anomalies**, across multiple commands and performance indicators.

The system is designed to:

* Detect both **small and large deviations**
* Support **multiple anomaly detection models**
* Provide **consistent inference output across models**
* Enable **side-by-side model comparison**

---

## 📊 Problem Context

EPP (Extensible Provisioning Protocol) systems generate high-volume operational metrics such as:

* Success / failure volumes
* Response time (latency)

These are aggregated **hourly per command**, and anomalies may indicate:

* System degradation
* Latency spikes
* Failure surges
* Traffic irregularities

---

## 🏗️ Architecture Overview

```
Data → Feature Engineering → Model → Thresholding → Inference → API → Dashboard
```

### Key Components

* **Data Generation / Input**
* **Feature Engineering (shared)**
* **Model-specific training & inference**
* **API (FastAPI)**
* **Dashboards (Streamlit)**

---

## 📁 Project Structure

```
.
├── configs/
├── data/
├── models/
│   └── v1/
│       ├── xgboost/
│       └── isolationforest/
├── src/
│   ├── common/
│   ├── xgboost_ad/
│   ├── isolationforest_ad/
│   ├── api/
│   └── pipeline/
├── dashboard/
│   └── pages/
└── .streamlit/
```

---

## ⚙️ Feature Engineering (Common Across Models)

All models share the same engineered features:

### 🕒 Time-based Features

* `hour_sin`
* `hour_cos`
  → Captures cyclic hourly patterns

### 🧩 Categorical Encoding

* One-hot encoding of `command`
  → e.g., `command_CHECK-DOMAIN`

### 🎯 Targets (for supervised models)

* `success_vol`
* `fail_vol`
* `success_rt_avg`
* `fail_rt_avg`

---

# 🤖 Models

---

## 1️⃣ XGBoost (Supervised Residual Model)

### 🔍 Approach

* Train regression models for each metric
* Predict **expected value**
* Compute **residual deviation**
* Compare against **learned thresholds**

### ⚙️ Pipeline

```
Features → XGBoost → Prediction → Residual → Threshold → Alert
```

### 📈 Strengths

* Detects **minor deviations precisely**
* Provides **root cause (metric-level)**
* Highly interpretable

### ⚠️ Limitations

* Requires threshold tuning
* Slightly more complex pipeline

---

## 2️⃣ Isolation Forest (Unsupervised Model)

### 🔍 Approach

* Learns **normal data distribution**
* Computes **anomaly score**
* Uses **auto-tuned threshold (percentile-based)**

### ⚙️ Pipeline

```
Features → IsolationForest → Score → Threshold → Alert
```

### 📈 Strengths

* No labels required
* Simple training pipeline
* Good for unknown anomaly patterns

### ⚠️ Limitations

* No direct root cause
* Sensitive to data distribution
* May miss subtle structured deviations

---

## 🔁 Thresholding Strategy

### XGBoost

* Residual-based thresholds
* Percentile tuning per metric

### Isolation Forest

* Score-based threshold
* Auto-tuned using:

  ```
  percentile(score, target_alert_rate)
  ```

---

## 🚀 Running the Pipeline

### Train

```bash
python -m pipeline.run_pipeline_xgboost --step train
python -m pipeline.run_pipeline_isolationforest --step train
```

### Inference

```bash
python -m pipeline.run_pipeline_xgboost --step inference
python -m pipeline.run_pipeline_isolationforest --step inference
```

---

## 🌐 API (FastAPI)

Start server:

```bash
uvicorn api.app:app
```

### Endpoints

#### Single Model

```
POST /predict
```

#### Multi-Model Comparison

```
POST /compare
```

---

## 📊 Dashboards (Streamlit)

### Run dashboard

```bash
cd epp-sla-anomaly-ui
pip install -e .
PYTHONPATH=src streamlit run src/dashboard/app.py
```

### MLflow UI

```bash
.venv/bin/mlflow ui \
  --backend-store-uri sqlite:///$PWD/mlflow.db \
  --registry-store-uri sqlite:///$PWD/mlflow.db \
  --default-artifact-root file://$PWD/mlartifacts \
  --port 5000
```

### Migrate Existing MLflow Runs

```bash
.venv/bin/mlflow experiments migrate-filestore \
  --src-store-uri file://$PWD/mlruns \
  --dest-store-uri sqlite:///$PWD/mlflow.db
```

---

### 🧭 Available Views

#### 1. Single Model Dashboard

* Select model (XGBoost / Isolation Forest)
* View alerts, trends, severity

#### 2. Comparison Dashboard

* Multi-model selection
* Overlap analysis
* Agreement / disagreement
* Time-series comparison
* Severity distribution

---

## 🔬 Key Capabilities

* Detect **minor SLA deviations**
* Compare **multiple models**
* Provide **consistent alert schema**
* Enable **interactive exploration**

---

## 📌 Future Enhancements

* Hybrid model (XGBoost + Isolation Forest)
* Drift detection
* Online / streaming inference
* Auto model selection
* Precision / recall benchmarking

---

## 💡 Summary

This system provides a **flexible, extensible framework** for anomaly detection in EPP SLA metrics, combining:

* **Precision (XGBoost)**
* **Generality (Isolation Forest)**

to deliver robust anomaly detection across diverse scenarios.
