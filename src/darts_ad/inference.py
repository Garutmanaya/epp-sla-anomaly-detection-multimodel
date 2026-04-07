# =========================================
# MODULE: darts_ad.inference
# PURPOSE: End-to-End Inference Pipeline
# =========================================

import pandas as pd
from common.config import load_config
from common.config_loader import (
    get_active_version,
    resolve_version_path,
    get_data_filename
)
from common.feature_engineering import prepare_features
from darts_ad.inference_engine import InferenceEngine
from common.model_registry import get_model, is_model_loaded

def load_data(cfg):
    """Loads CSV data based on active versioning."""
    filename = get_data_filename()
    path = resolve_version_path("data", filename, cfg.version)
    return pd.read_csv(path)

def run_inference(df):
    """Reusable inference logic for both CLI and API usage."""
    version = get_active_version()
    cfg = load_config(version)

    # 1. Pre-process (Scalers/Cleaning)
    df = df.copy()
    df = prepare_features(df)

    # 2. Get Engine (Shared Registry or New Instance)
    if is_model_loaded("darts_hybrid"):
        engine = get_model("darts_hybrid")
    else:
        engine = InferenceEngine(version)

    # 3. Process Logic
    df = engine.predict(df)
    results = engine.detect(df)

    return results

def main():
    """Main entry point for local testing and verification."""
    version = get_active_version()
    cfg = load_config(version)

    print(f"--- Running Hybrid Inference (Version: {version}) ---")
    
    # Load test data
    df = load_data(cfg)

    # Run pipeline
    results = run_inference(df)

    # Calculate Summary Metrics
    total = len(results)
    alerts = (results["Status"] != "Normal ✅").sum()

    print(f"Total Records: {total}")
    print(f"Alerts Found:  {alerts}")
    print(f"Alert Rate:    {round(alerts/total*100, 2)}%")
    
    # Preview top results
    print("\nSample Output:")
    print(results[['timestamp', 'value', 'Anomaly_Score', 'Status']].head(20))

if __name__ == "__main__":
    main()
