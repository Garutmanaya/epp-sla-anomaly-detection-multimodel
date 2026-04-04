# =========================================
# MODULE: train (Isolation Forest)
# =========================================

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from common.config_loader import get_active_version, get_data_filename, resolve_version_path
from common.feature_engineering import prepare_features, align_features
from isolationforest_ad.local_utils import get_model_path


TARGET_ALERT_RATE = 0.01   # 1%


def main():

    version = get_active_version()

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

    # ---------------------------------
    # SAVE BUNDLE
    # ---------------------------------
    bundle = {
        "model": model,
        "features": FEATURES,
        "threshold": float(threshold),
        "model_type": "isolationforest"
    }

    model_path = get_model_path(version)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(bundle, model_path)

    print(f"Model saved: {model_path}")
    print("Score stats:")
    print(f"min: {scores.min()}")
    print(f"max: {scores.max()}")
    print(f"mean: {scores.mean()}")
    print(f"threshold: {threshold}")


if __name__ == "__main__":
    main()