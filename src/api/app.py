# =========================================
# MODULE: FastAPI (clean unified version)
# =========================================

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd
import time

from common.model_registry import register_model, get_model
from common.config_loader import get_active_version, get_flag
from common.s3_utils import download_models_for_version

from xgboost_ad.inference_engine import InferenceEngine as XGBEngine
from isolationforest_ad.inference_engine import InferenceEngine as IFEngine
from common.feature_engineering import prepare_features 

app = FastAPI(title="EPP-SLA-Anomaly Detection API")


# =========================================
# REQUEST SCHEMA (UNIFIED)
# =========================================
class Record(BaseModel):
    timestamp: str
    command: str
    success_vol: float
    success_rt_avg: float
    fail_vol: float
    fail_rt_avg: float


class InferenceRequest(BaseModel):
    models: List[str]   # ALWAYS list
    data: List[Record]


# =========================================
# HEALTH
# =========================================
@app.get("/")
def health():
    return {"status": "ok"}


# =========================================
# CORE EXECUTION (REUSABLE)
# =========================================
def run_models(df: pd.DataFrame, models: List[str]):

    df = prepare_features(df)
    output = {}
    meta = {}

    for model in models:

        start = time.time()

        engine = get_model(model)

        temp_df = df.copy()
        temp_df = engine.predict(temp_df)
        results = engine.detect(temp_df)

        latency = round((time.time() - start) * 1000, 2)

        output[model] = results.to_dict(orient="records")

        meta[model] = {
            "latency_ms": latency,
            "records": len(results)
        }

    return output, meta


# =========================================
# API ENDPOINT (SINGLE + MULTI)
# =========================================
@app.post("/predict")
def predict(req: InferenceRequest):

    df = pd.DataFrame([r.dict() for r in req.data])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    results, metadata = run_models(df, req.models)

    return {
        "results": results,
        "metadata": metadata
    }


# =========================================
# SAGEMAKER COMPATIBILITY
# =========================================
@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.post("/invocations")
def invocations(payload: dict):

    df = pd.DataFrame(payload["data"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    models = payload.get("models", [])

    if not models:
        return {"error": "Provide 'models'"}

    results, metadata = run_models(df, models)

    return {
        "results": results,
        "metadata": metadata
    }


# =========================================
# STARTUP -- Load Models
# =========================================
@app.on_event("startup")
def load_models():

    version = get_active_version()

    print("🚀 Loading models...")

    if get_flag("download_from_s3"):
        print("Downloading models from S3...")
        download_models_for_version(version)

    register_model("xgboost", XGBEngine(version))
    register_model("isolationforest", IFEngine(version))

    print("✅ Models loaded")


# =========================================
# RUN
# uvicorn api.app:app --port 8000
# =========================================

