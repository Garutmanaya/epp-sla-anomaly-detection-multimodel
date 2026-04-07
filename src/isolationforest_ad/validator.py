from isolationforest_ad.inference import run_inference
from datetime import datetime

import mlflow

from common.config import load_config
from common.config_loader import get_active_version
from common.mlflow_utils import configure_mlflow
from shared.data_dictionary import NORMAL_STATUS
from shared.demo_data import generate_test_data

def evaluate_model(df, results_df):
    merged = results_df.copy()
    merged["is_actual_anomaly"] = df["is_anomaly"].values

    total = len(merged)
    alerts = (merged["Status"] != NORMAL_STATUS).sum()
    actual = merged["is_actual_anomaly"].sum()

    tp = ((merged["Status"] != NORMAL_STATUS) & merged["is_actual_anomaly"]).sum()
    fp = ((merged["Status"] != NORMAL_STATUS) & ~merged["is_actual_anomaly"]).sum()
    fn = ((merged["Status"] == NORMAL_STATUS) & merged["is_actual_anomaly"]).sum()

    precision = tp / (tp + fp + 1e-6)
    recall = tp / (tp + fn + 1e-6)
    alert_rate = alerts / total if total else 0

    print("\n===== MODEL PERFORMANCE =====")
    print(f"Total Records: {total}")
    print(f"Actual Anomalies: {actual}")
    print(f"Detected Alerts: {alerts}")
    print(f"\nPrecision: {round(precision, 3)}")
    print(f"Recall: {round(recall, 3)}")
    print(f"Alert Rate: {round(alert_rate, 3)}")

    mlflow.log_metrics(
        {
            "precision": precision,
            "recall": recall,
            "alert_rate": alert_rate,
        }
    )


def main():
    version = get_active_version()
    cfg = load_config(version)

    configure_mlflow()

    with mlflow.start_run(run_name=f"validate_{cfg.version}_isolationforest"):
        df = generate_test_data(
            start_date=datetime(2026, 5, 1),
            hours=48,
            anomaly_prob=0.2
        )

        results = run_inference(df)
        evaluate_model(df, results)

        print("\nSample Output:")
        print(results.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
