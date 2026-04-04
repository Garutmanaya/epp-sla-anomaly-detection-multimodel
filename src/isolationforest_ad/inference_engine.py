# =========================================
# MODULE: inference_engine
# =========================================

import joblib
import pandas as pd

from common.config_loader import get_flag
from common.feature_engineering import align_features
from common.s3_utils import download_file
from isolationforest_ad.local_utils import get_model_path, get_model_s3_key


class InferenceEngine:

    def __init__(self, version):

        self.version = version

        model_path = get_model_path(version)

        if get_flag("download_from_s3"):
            try:
                download_file(get_model_s3_key(version), str(model_path))
            except Exception as e:
                print(f"S3 download failed: {e}")

        bundle = joblib.load(model_path)

        self.model = bundle["model"]
        self.features = bundle["features"]
        self.threshold = bundle["threshold"]

    # =========================================
    # PREDICT
    # =========================================
    def predict(self, df):

        df = df.copy()

        X = align_features(df, self.features)

        df["anomaly_score"] = self.model.decision_function(X)

        return df

    # =========================================
    # DETECT
    # =========================================
    def detect(self, df):

        results = []

        # ✅ FIX: use distribution-based scaling
        score_std = df["anomaly_score"].std() + 1e-6

        for _, row in df.iterrows():

            score = row["anomaly_score"]
            is_anomaly = score <= self.threshold  # ✅ boundary-safe

            if is_anomaly:

                # ✅ FIX: stable severity calculation
                gap = self.threshold - score
                severity = gap / score_std
                severity = max(severity, 0)
                severity = min(severity, 5)

                results.append({
                    "Timestamp": row["timestamp"],
                    "Command": row["command"],
                    "Hour": row["hour"],
                    "Status": self.get_severity_label(severity),
                    "Severity": round(severity, 2),
                    "Root_Cause": "anomaly_score",
                    "Actual": str(round(score, 4)),
                    "Expected": str(round(self.threshold, 4)),
                    "Deviation": str(round(gap, 6))   # ✅ FIX: real gap, not %
                })

            else:
                results.append({
                    "Timestamp": row["timestamp"],
                    "Command": row["command"],
                    "Hour": row["hour"],
                    "Status": "Normal ✅",
                    "Severity": 0,
                    "Root_Cause": "None",
                    "Actual": "-",
                    "Expected": "-",
                    "Deviation": "-"
                })

        return pd.DataFrame(results)

    # =========================================
    # SEVERITY LABEL
    # =========================================
    def get_severity_label(self, severity):

        if severity < 1:
            return "LOW ⚠️"
        elif severity < 2:
            return "MEDIUM ⚠️"
        else:
            return "CRITICAL 🚨"