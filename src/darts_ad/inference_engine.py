# =========================================
# MODULE: darts_ad.inference_engine
# PURPOSE: Hybrid Model Logic & Transformation
# =========================================

import os
import joblib
import pandas as pd
from darts import TimeSeries
from darts.models import XGBModel
from common.config_loader import resolve_version_path

class InferenceEngine:
    def __init__(self, version):
        self.version = version
        # Resolve the version-specific path for models
        self.model_dir = resolve_version_path("models/darts_ad", "", version)
        
        # Load the saved forecasting and scoring components
        self.forecaster = XGBModel.load(os.path.join(self.model_dir, "xgb_forecaster.pt"))
        self.scorer = joblib.load(os.path.join(self.model_dir, "if_scorer.joblib"))

    def predict(self, df):
        """
        Processes the dataframe and adds anomaly scores.
        """
        # Convert DF to Darts format
        temp_df = df.copy()
        temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
        series = TimeSeries.from_dataframe(temp_df, time_col='timestamp', value_cols='value')
        
        # Generate Raw Anomaly Scores (from Isolation Forest)
        # result is a TimeSeries of scores
        scores_ts = self.scorer.score(series)
        
        # Flatten and attach to the original dataframe
        # Note: Ensure alignment if using lags; Darts handles padding internally
        df["Anomaly_Score"] = scores_ts.values().flatten()
        
        return df

    def detect(self, df, threshold=0.8):
        """
        Applies classification labels based on Anomaly_Score.
        """
        df["Status"] = df["Anomaly_Score"].apply(
            lambda x: "🚨 ANOMALY" if x > threshold else "Normal ✅"
        )
        return df