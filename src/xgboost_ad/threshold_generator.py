# =========================================
# MODULE: threshold_generator
# PURPOSE: Generate anomaly thresholds (hybrid + auto-tuned)
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd
import mlflow

from common.config import load_config
from common.config_loader import (
    resolve_version_path,
    get_data_filename,
    get_active_version,
)
from common.feature_engineering import (
    prepare_features,
    align_features
)
from common.mlflow_utils import configure_mlflow
from xgboost_ad.local_utils import load_model_bundle, save_model_bundle


# =========================================
# COMPUTE RESIDUALS
# =========================================
def compute_residuals(df, targets):

    df = df.copy()

    for t in targets:
        df[f"{t}_ratio"] = abs(df[t] - df[f"{t}_pred"]) / (df[f"{t}_pred"] + 1e-6)
        df[f"{t}_abs_dev"] = abs(df[t] - df[f"{t}_pred"])

    return df


# =========================================
# BUILD BASE THRESHOLDS
# =========================================
def build_base_thresholds(df, cfg):

    thresholds = {}

    grouped = df.groupby(["command", "hour"])

    for (cmd, hr), group in grouped:

        thresholds.setdefault(cmd, {})

        for t in cfg.model.targets:

            ratios = group[f"{t}_ratio"].dropna()
            abs_dev = group[f"{t}_abs_dev"].dropna()

            if len(ratios) < 10:
                continue

            percent_thr = ratios.quantile(cfg.threshold.percentile)
            abs_thr = abs_dev.quantile(cfg.threshold.percentile)

            thresholds[cmd][t] = {
                "percent_threshold": float(percent_thr),
                "abs_threshold": float(abs_thr)
            }

    return thresholds


# =========================================
# EVALUATE ALERT RATE
# =========================================
def compute_alert_rate(df, thresholds, cfg, factor):

    total = len(df)
    alerts = 0

    for _, row in df.iterrows():

        cmd = row["command"]
        hour = row["hour"]

        for t in cfg.model.targets:

            if cmd not in thresholds:
                continue
            if t not in thresholds[cmd]:
                continue

            rule = thresholds[cmd][t]

            percent_thr = rule["percent_threshold"] * factor
            abs_thr = rule["abs_threshold"]

            expected = row[f"{t}_pred"]
            actual = row[t]

            threshold_val = max(expected * percent_thr, abs_thr)
            deviation = abs(actual - expected)

            if deviation > threshold_val:
                alerts += 1
                break  # one alert per row

    return alerts / total


# =========================================
# AUTO-TUNE FACTOR
# =========================================
def auto_tune_factor(df, thresholds, cfg):

    best_factor = 1.0
    best_diff = float("inf")

    for factor in cfg.threshold.factor_range:

        alert_rate = compute_alert_rate(df, thresholds, cfg, factor)

        diff = abs(alert_rate - cfg.threshold.target_alert_rate)

        if diff < best_diff:
            best_diff = diff
            best_factor = factor

        print(f"Factor {factor:.2f} → Alert Rate: {alert_rate:.4f}")

    print(f"\nBest factor selected: {best_factor:.2f}")

    mlflow.log_metric("best_factor", best_factor)

    return best_factor


# =========================================
# APPLY FACTOR
# =========================================
def apply_factor(thresholds, factor):

    final_thresholds = {}

    for cmd in thresholds:
        final_thresholds.setdefault(cmd, {})

        for t in thresholds[cmd]:

            rule = thresholds[cmd][t]

            final_thresholds[cmd][t] = {
                "percent_threshold": rule["percent_threshold"] * factor,
                "abs_threshold": rule["abs_threshold"]
            }

    return final_thresholds


# =========================================
# UPDATE MODEL BUNDLE
# =========================================
def update_model_bundle_with_thresholds(thresholds, cfg):
    bundle = load_model_bundle(cfg.version)

    bundle["thresholds"] = {
        "default_baselines": thresholds,
        "hourly_overrides": {}
    }

    model_path = save_model_bundle(bundle, cfg.version)

    print(f"Thresholds added to model bundle: {model_path}")

    mlflow.log_artifact(model_path)


# =========================================
# MAIN
# =========================================
def main():

    version = get_active_version()
    cfg = load_config(version)

    configure_mlflow()

    with mlflow.start_run(run_name=f"thresholds_{cfg.version}"):

        # Load model bundle
        bundle = load_model_bundle(cfg.version)

        models = bundle["models"]
        FEATURES = bundle["features"]

        # Load data
        filename = get_data_filename()

        data_path = resolve_version_path(
            base_dir="data",
            filename=filename,
            version=cfg.version
        )

        df = pd.read_csv(data_path)

        # Features
        df = prepare_features(df)
        X = align_features(df, FEATURES)

        # Predictions
        for t in cfg.model.targets:
            df[f"{t}_pred"] = models[t].predict(X)

        # Residuals
        df = compute_residuals(df, cfg.model.targets)

        # Base thresholds
        base_thresholds = build_base_thresholds(df, cfg)

        # Auto-tune factor
        best_factor = auto_tune_factor(df, base_thresholds, cfg)

        # Final thresholds
        final_thresholds = apply_factor(base_thresholds, best_factor)

        # Save into model bundle
        update_model_bundle_with_thresholds(final_thresholds, cfg)

        print("Threshold generation complete")


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    main()
