# =========================================
# MODULE: validator
# PURPOSE: Generate dynamic test data + evaluate model
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import mlflow
from common.config import load_config
from common.config_loader import (
    get_active_version,
    resolve_version_path,
    get_data_filename,
    get_project_root,
    load_main_config,
)
from common.feature_engineering import prepare_features
from xgboost_ad.inference_engine import InferenceEngine
from common.config import load_config
from common.data_generator import load_generator_config
from xgboost_ad.inference import run_inference

np.random.seed(42)


# =========================================
# LOAD CONFIG (REUSE GENERATOR LOGIC)
# =========================================
def load_generator_rules():

    config = load_generator_config()

    return (
        config["randomness"],
        config["commands"],
        config["hourly_rules"]
    )


# =========================================
# HELPERS
# =========================================
def add_noise(value, pct):
    return value * (1 + np.random.uniform(-pct, pct))


def random_in_range(low, high, pct):
    base = np.random.uniform(low, high)
    return add_noise(base, pct)


# =========================================
# APPLY HOURLY RULES
# =========================================
def apply_hourly_rules(cmd, hour, values, hourly_rules):

    hour_str = str(hour)

    if hour_str in hourly_rules:
        if cmd in hourly_rules[hour_str]:
            rules = hourly_rules[hour_str][cmd]

            for key, multiplier in rules.items():
                field = key.replace("_multiplier", "")
                values[field] *= multiplier

    return values


# =========================================
# INJECT ANOMALY (ONE METRIC)
# =========================================
def inject_anomaly(values):

    metric = np.random.choice([
        "success_vol",
        "fail_vol",
        "success_rt",
        "fail_rt"
    ])

    direction = np.random.choice(["up", "down"])

    factor = np.random.uniform(3, 10) if direction == "up" else np.random.uniform(0.1, 0.5)

    values[metric] *= factor

    return values, f"{metric}_{direction}"


# =========================================
# GENERATE TEST DATA
# =========================================
def generate_test_data(start_date, hours, anomaly_prob=0.2):

    randomness, commands_config, hourly_rules = load_generator_rules()

    # ---------------------------------
    # FIX: normalize input
    # ---------------------------------
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
        
    data = []
    current = start_date

    for _ in range(hours):

        hour = current.hour

        for cmd, cfg in commands_config.items():

            values = {
                "success_vol": add_noise(cfg["success_vol"], randomness),
                "fail_vol": add_noise(cfg["fail_vol"], randomness),
                "success_rt": random_in_range(*cfg["success_rt"], randomness),
                "fail_rt": random_in_range(*cfg["fail_rt"], randomness)
            }

            values = apply_hourly_rules(cmd, hour, values, hourly_rules)

            is_anomaly = False
            anomaly_type = "normal"

            if np.random.rand() < anomaly_prob:
                values, anomaly_type = inject_anomaly(values)
                is_anomaly = True

            data.append({
                "timestamp": current,
                "command": cmd,
                "success_vol": int(values["success_vol"]),
                "success_rt_avg": round(values["success_rt"], 3),
                "fail_vol": int(values["fail_vol"]),
                "fail_rt_avg": round(values["fail_rt"], 3),
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type
            })

        current += timedelta(hours=1)

    return pd.DataFrame(data)


# =========================================
# EVALUATE MODEL
# =========================================
def evaluate_model(df, results_df, cfg):

    merged = results_df.copy()
    merged["is_actual_anomaly"] = df["is_anomaly"].values

    total = len(merged)
    alerts = (merged["Status"] != "Normal ✅").sum()
    actual = merged["is_actual_anomaly"].sum()

    tp = ((merged["Status"] != "Normal ✅") & merged["is_actual_anomaly"]).sum()
    fp = ((merged["Status"] != "Normal ✅") & ~merged["is_actual_anomaly"]).sum()
    fn = ((merged["Status"] == "Normal ✅") & merged["is_actual_anomaly"]).sum()

    precision = tp / (tp + fp + 1e-6)
    recall = tp / (tp + fn + 1e-6)
    alert_rate = alerts / total

    print("\n===== MODEL PERFORMANCE =====")
    print(f"Total Records: {total}")
    print(f"Actual Anomalies: {actual}")
    print(f"Detected Alerts: {alerts}")

    print(f"\nPrecision: {round(precision, 3)}")
    print(f"Recall: {round(recall, 3)}")
    print(f"Alert Rate: {round(alert_rate, 3)}")

    # ✅ MLflow logging
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)
    mlflow.log_metric("alert_rate", alert_rate)


# =========================================
# MAIN
# =========================================
def main():

    version = get_active_version()
    cfg = load_config(version)

    root = get_project_root()
    mlflow.set_tracking_uri(f"file:{root}/mlruns")
    mlflow.set_experiment("anomaly-detection")

    with mlflow.start_run(run_name=f"validate_{cfg.version}"):

        df = generate_test_data(
            start_date=datetime(2026, 5, 1),
            hours=48,
            anomaly_prob=0.2
        )

        results_df = run_inference(df)

        evaluate_model(df, results_df, cfg)

        print("\nSample Output:")
        print(results_df.head(20).to_string(index=False))


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    main()