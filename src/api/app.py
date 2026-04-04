# =========================================
# MODULE: FastAPI (multi-model)
# =========================================

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd

from api.model_registry import get_model_runner

app = FastAPI(title="EPP-SLA-Anomaly Detection API")


# =========================================
# REQUEST SCHEMA
# =========================================
class Record(BaseModel):
    timestamp: str
    command: str
    success_vol: float
    success_rt_avg: float
    fail_vol: float
    fail_rt_avg: float


class PredictRequest(BaseModel):
    model: str                # single model
    data: List[Record]


class CompareRequest(BaseModel):
    models: List[str]         # multiple models
    data: List[Record]


# =========================================
# HEALTH
# =========================================
@app.get("/")
def health():
    return {"status": "ok"}


# =========================================
# SINGLE MODEL INFERENCE
# =========================================
@app.post("/predict")
def predict(req: PredictRequest):

    df = pd.DataFrame([r.dict() for r in req.data])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    runner = get_model_runner(req.model)

    results = runner(df)

    return {
        "model": req.model,
        "results": results.to_dict(orient="records")
    }


# =========================================
# MULTI-MODEL COMPARISON
# =========================================
@app.post("/compare")
def compare(req: CompareRequest):

    df = pd.DataFrame([r.dict() for r in req.data])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    output = {}

    for model in req.models:
        runner = get_model_runner(model)
        results = runner(df)
        output[model] = results.to_dict(orient="records")

    return output

# =========================================
# run
# uvicorn api.app:app --reload --port 8000 
# =========================================
