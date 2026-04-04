# =========================================
# MODULE: inference_engine
# PURPOSE: Stateful anomaly detection engine
# =========================================

# =========================================
# IMPORTS
# =========================================
import joblib
import pandas as pd

from common.config_loader import resolve_version_path, get_flag
from common.feature_engineering import align_features
from common.s3_utils import download_file, build_s3_key
from xgboost_ad.local_utils import get_model_path, get_model_s3_key 

# =========================================
# ENGINE
# =========================================
class InferenceEngine:

    def __init__(self, version):
        """
        Initialize inference engine with model + thresholds
        """

        self.version = version

        # ---------------------------------
        # Load model bundle
        # ---------------------------------
        model_path = get_model_path(self.version)

        # Optional S3 download
        if get_flag("download_from_s3"):
            s3_key = get_model_s3_key(self.version)
            try:
                download_file(s3_key, str(model_path))
            except Exception as e:
                print(f"S3 download failed, using local model: {e}")
            
        bundle = joblib.load(model_path)

        self.models = bundle["models"]
        self.features = bundle["features"]
        self.targets = bundle["targets"]

        # ---------------------------------
        # Load thresholds from bundle
        # ---------------------------------
        if "thresholds" not in bundle:
            raise ValueError(
                "Thresholds not found in model bundle. Run threshold generator."
            )

        self.thresholds = bundle["thresholds"]
        self.default_baselines = self.thresholds["default_baselines"]
        self.hourly_overrides = self.thresholds["hourly_overrides"]

    # =========================================
    # THRESHOLD RESOLVER
    # =========================================
    def get_threshold(self, cmd, hour, metric):

        hour = str(hour)

        # Hourly override
        if hour in self.hourly_overrides:
            if cmd in self.hourly_overrides[hour]:
                if metric in self.hourly_overrides[hour][cmd]:
                    return self.hourly_overrides[hour][cmd][metric]

        # Default baseline
        if cmd in self.default_baselines:
            if metric in self.default_baselines[cmd]:
                return self.default_baselines[cmd][metric]

        return None

    # =========================================
    # PREDICT
    # =========================================
    def predict(self, df):

        df = df.copy()

        X = align_features(df, self.features)

        for t in self.targets:
            df[f"{t}_pred"] = self.models[t].predict(X)

        return df

    # =========================================
    # DETECT ANOMALIES
    # =========================================
    def detect(self, df):

        results = []

        for _, row in df.iterrows():

            cmd = row["command"]
            hour = row["hour"]

            culprit = None
            max_severity = 0

            for t in self.targets:

                rule = self.get_threshold(cmd, hour, t)

                if rule is None:
                    continue

                # Safety: ensure correct structure
                if "percent_threshold" not in rule or "abs_threshold" not in rule:
                    continue

                actual = row[t]
                expected = row[f"{t}_pred"]

                deviation = abs(actual - expected)

                # ---------------------------------
                # HYBRID THRESHOLD (KEY FIX)
                # ---------------------------------
                percent_thr = rule["percent_threshold"]
                abs_thr = rule["abs_threshold"]

                threshold_val = max(
                    expected * percent_thr,
                    abs_thr
                )

                severity = deviation / (threshold_val + 1e-6)

                if deviation > threshold_val:
                    if severity > max_severity:
                        max_severity = severity
                        culprit = {
                            "metric": t,
                            "actual": actual,
                            "expected": expected,
                            "severity": severity,
                            "deviation": deviation,
                            "threshold": threshold_val
                        }

            # ---------------------------------
            # BUILD RESULT
            # ---------------------------------
            if culprit:
                results.append({
                    "Timestamp": row["timestamp"],
                    "Command": cmd,
                    "Hour": hour,
                    "Status": self.get_severity_label(culprit["severity"]),
                    "Severity": round(culprit["severity"], 2),
                    "Root_Cause": culprit["metric"],
                    "Actual": str(round(culprit["actual"], 2)),
                    "Expected": str(round(culprit["expected"], 2)),
                    "Deviation": str(f"{round(culprit['severity'] * 100, 1)}%")
                })
            else:
                results.append({
                    "Timestamp": row["timestamp"],
                    "Command": cmd,
                    "Hour": hour,
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

        if severity < 1.5:
            return "LOW ⚠️"
        elif severity < 3:
            return "MEDIUM ⚠️"
        else:
            return "CRITICAL 🚨"