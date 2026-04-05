# =========================================
# SAGEMAKER INFERENCE ENTRY
# =========================================

import json
import pandas as pd

from api.model_registry import get_model_runner


# -----------------------------
# Load model (optional preload)
# -----------------------------
def model_fn(model_dir):
    return None  # not needed (we load per request)


# -----------------------------
# Input parser
# -----------------------------
def input_fn(request_body, content_type):

    if content_type == "application/json":
        data = json.loads(request_body)
        return data

    raise ValueError("Unsupported content type")


# -----------------------------
# Predict
# -----------------------------
import time

def predict_fn(input_data, model):

    model_name = input_data["model"]
    records = input_data["data"]

    start = time.time()

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    runner = get_model_runner(model_name)
    results = runner(df)

    latency = round((time.time() - start) * 1000, 2)

    return {
        "results": {
            model_name: results.to_dict(orient="records")
        },
        "metadata": {
            model_name: {
                "latency_ms": latency,
                "records": len(results)
            }
        }
    }

# -----------------------------
# Output formatter
# -----------------------------
def output_fn(prediction, accept):

    return json.dumps({
        "results": prediction.to_dict(orient="records")
    }), "application/json"
