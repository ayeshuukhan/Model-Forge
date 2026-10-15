import logging
import time
import os
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO,
                     format='{"timestamp":"%(asctime)s","service":"regression-service","level":"%(levelname)s","event":"%(message)s"}')
logger = logging.getLogger("regression-service")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "regression_model.joblib")

app = FastAPI(title="Regression Service")

PREDICTIONS_TOTAL = Counter(
    "model_predictions_total", "Total predictions made", ["model", "status"]
)
PREDICTION_LATENCY = Histogram(
    "inference_latency_seconds", "Prediction latency in seconds", ["model"]
)

_model = None


@app.on_event("startup")
def load_model():
    global _model
    if not os.path.exists(MODEL_PATH):
        logger.warning("model file not found, training on startup")
        import subprocess
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "..", "model", "train.py")], check=True)
    _model = joblib.load(MODEL_PATH)
    logger.info("model loaded successfully")


class RegressionRequest(BaseModel):
    features: List[float] = Field(..., min_length=4, max_length=4,
                                   description="[sqft, bedrooms, bathrooms, age_years]")

    @field_validator("features")
    @classmethod
    def validate_features(cls, v):
        if any(x < 0 for x in v):
            raise ValueError("features must be non-negative")
        return v


class RegressionResponse(BaseModel):
    model: str = "regression"
    prediction: float


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if _model is None:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=RegressionResponse)
def predict(req: RegressionRequest):
    if _model is None:
        PREDICTIONS_TOTAL.labels(model="regression", status="error").inc()
        raise HTTPException(status_code=503, detail="model not ready")

    start = time.time()
    try:
        X = np.array([req.features])
        pred = float(_model.predict(X)[0])
        PREDICTIONS_TOTAL.labels(model="regression", status="success").inc()
        return RegressionResponse(prediction=round(pred, 2))
    except Exception as e:
        PREDICTIONS_TOTAL.labels(model="regression", status="error").inc()
        logger.error(f"prediction failed: {e}")
        raise HTTPException(status_code=500, detail="inference failed")
    finally:
        PREDICTION_LATENCY.labels(model="regression").observe(time.time() - start)
