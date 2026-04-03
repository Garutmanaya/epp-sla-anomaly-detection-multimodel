# =========================================
# MODULE: FastAPI Service
# =========================================

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pandas as pd

from anomaly_detection.inference.inference import run_inference

app = FastAPI(title="Anomaly Detection API")


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


# =========================================
# HEALTH CHECK
# =========================================
@app.get("/")
def health():
    return {"status": "ok"}


# =========================================
# INFERENCE ENDPOINT
# =========================================
@app.post("/predict")
def predict(records: List[Record]):

    df = pd.DataFrame([r.dict() for r in records])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    results = run_inference(df)

    return results.to_dict(orient="records")

# =========================================
# Run example from cli 
# =========================================
# uvicorn anomaly_detection.api.main:app --reload --port 8000
