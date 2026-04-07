# =========================================
# MODULE: darts_ad.train
# PURPOSE: Train Hybrid Darts (XGBoost + IF)
# =========================================

import os
import joblib
import pandas as pd
from darts import TimeSeries
from darts.models import XGBModel
from darts.ad import PyODScorer
from pyod.models.iforest import IForest

from common.config_loader import (
    get_active_version,
    resolve_version_path,
    get_data_filename
)
from common.config import load_config

def train_model():
    # 1. Setup Versioning & Paths
    version = get_active_version()
    cfg = load_config(version)
    
    data_file = get_data_filename()
    data_path = resolve_version_path("data", data_file, version)
    
    # 2. Load and Prepare Data
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert to Darts TimeSeries
    series = TimeSeries.from_dataframe(df, time_col='timestamp', value_cols='value')
    
    # 3. Initialize & Train Forecaster (Supervised)
    # Lags defined by config or default to 12
    forecaster = XGBModel(lags=12, output_chunk_length=1, n_estimators=100)
    print(f"Training XGBoost Forecaster for version: {version}...")
    forecaster.fit(series)
    
    # 4. Initialize & Train Scorer (Unsupervised)
    # Using Isolation Forest from PyOD via Darts wrapper
    if_model = IForest(contamination=0.05, n_estimators=100)
    scorer = PyODScorer(model=if_model)
    print("Training Isolation Forest Scorer...")
    scorer.fit(series)
    
    # 5. Save Artifacts to Versioned Directory
    model_dir = resolve_version_path("models/darts_ad", "", version)
    os.makedirs(model_dir, exist_ok=True)
    
    forecaster.save(os.path.join(model_dir, "xgb_forecaster.pt"))
    joblib.dump(scorer, os.path.join(model_dir, "if_scorer.joblib"))
    
    print(f"✅ Successfully saved Hybrid Darts models to {model_dir}")

if __name__ == "__main__":
    train_model()