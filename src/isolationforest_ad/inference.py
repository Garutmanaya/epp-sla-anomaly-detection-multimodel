# =========================================
# MODULE: inference
# PURPOSE: Run inference pipeline end-to-end (Isolation Forest)
# =========================================

# =========================================
# IMPORTS
# =========================================
import pandas as pd

from common.config import load_config
from common.config_loader import (
    get_active_version,
    resolve_version_path,
    get_data_filename
)
from common.feature_engineering import prepare_features
from isolationforest_ad.inference_engine import InferenceEngine
from common.model_registry import get_model, is_model_loaded

# =========================================
# LOAD DATA
# =========================================
def load_data(cfg):

    filename = get_data_filename()

    path = resolve_version_path(
        base_dir="data",
        filename=filename,
        version=cfg.version
    )

    return pd.read_csv(path)


# =========================================
# RUN INFERENCE (REUSABLE)
# =========================================
def run_inference(df):

    version = get_active_version()
    cfg = load_config(version)

    df = df.copy()
    df = prepare_features(df)

    # ---------------------------------
    # Use preloaded model if available
    # ---------------------------------
    if is_model_loaded("isolationforest"):
        engine = get_model("isolationforest")
    else:
        # fallback (pipeline / CLI mode)
        engine = InferenceEngine(version)
    
    df = engine.predict(df)
    results = engine.detect(df)

    return results


# =========================================
# MAIN
# =========================================
def main():

    version = get_active_version()
    cfg = load_config(version)

    # Load data
    filename = get_data_filename()

    path = resolve_version_path(
        base_dir="data",
        filename=filename,
        version=cfg.version
    )

    df = pd.read_csv(path)

    # Run inference
    results = run_inference(df)

    total = len(results)
    alerts = (results["Status"] != "Normal ✅").sum()

    print(f"Total: {total}")
    print(f"Alerts: {alerts}")
    print(f"Alert Rate: {round(alerts/total*100, 2)}%")

    print(results.head(20))


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    main()
