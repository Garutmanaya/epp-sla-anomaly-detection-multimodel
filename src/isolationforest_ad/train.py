import numpy as np
import pandas as pd
import mlflow
from sklearn.ensemble import IsolationForest

from common.config import load_config
from common.config_loader import (
    get_active_version,
    get_data_filename,
    get_flag,
    resolve_version_path,
)
from common.feature_engineering import prepare_features, align_features
from common.mlflow_utils import configure_mlflow
from common.s3_utils import upload_file
from isolationforest_ad.local_utils import get_model_s3_key, save_model_bundle


TARGET_ALERT_RATE = 0.01   # 1%


def main():

    version = get_active_version()
    cfg = load_config(version)

    configure_mlflow()

    with mlflow.start_run(run_name=f"train_{version}_isolationforest"):
        mlflow.log_param("version", version)
        mlflow.log_params(
            {
                "model_type": "isolationforest",
                "n_estimators": 100,
                "contamination": TARGET_ALERT_RATE,
                "random_state": 42,
            }
        )

        # Load data
        data_path = resolve_version_path(
            base_dir="data",
            filename=get_data_filename(),
            version=version
        )

        df = pd.read_csv(data_path)
        df = prepare_features(df)

        FEATURES = [c for c in df.columns if c.startswith("hour_") or c.startswith("command_")]
        X = align_features(df, FEATURES)

        mlflow.log_metric("training_rows", len(df))
        mlflow.log_metric("feature_count", len(FEATURES))

        # Train model
        model = IsolationForest(
            n_estimators=100,
            contamination=TARGET_ALERT_RATE,
            random_state=42
        )

        model.fit(X)

        # ---------------------------------
        # AUTO-TUNE THRESHOLD
        # ---------------------------------
        scores = model.decision_function(X)

        raw_threshold = np.percentile(scores, TARGET_ALERT_RATE * 100)

        # avoid edge-case collapse
        threshold = raw_threshold + (scores.std() * 0.5)

        print(f"Raw threshold: {raw_threshold}")
        print(f"Adjusted threshold: {threshold}")

        mlflow.log_metrics(
            {
                "score_min": float(scores.min()),
                "score_max": float(scores.max()),
                "score_mean": float(scores.mean()),
                "score_std": float(scores.std()),
                "raw_threshold": float(raw_threshold),
                "adjusted_threshold": float(threshold),
            }
        )

        # ---------------------------------
        # SAVE BUNDLE
        # ---------------------------------
        bundle = {
            "model": model,
            "features": FEATURES,
            "threshold": float(threshold),
            "model_type": "isolationforest",
            "version": version,
        }

        model_path = save_model_bundle(bundle, version)

        print(f"Model saved: {model_path}")
        print("Score stats:")
        print(f"min: {scores.min()}")
        print(f"max: {scores.max()}")
        print(f"mean: {scores.mean()}")
        print(f"threshold: {threshold}")

        mlflow.log_artifact(model_path)

        if get_flag("upload_to_s3"):
            upload_file(str(model_path), get_model_s3_key(version))

    print("Training complete")

if __name__ == "__main__":
    main()
