import logging
import time
import os
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO,
                     format='{"timestamp":"%(asctime)s","service":"sentiment-service","level":"%(levelname)s","event":"%(message)s"}')
logger = logging.getLogger("sentiment-service")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "sentiment_model.joblib")

app = FastAPI(title="Sentiment Service")

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


class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class SentimentResponse(BaseModel):
    model: str = "sentiment"
    sentiment: str
    confidence: float


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


@app.post("/predict", response_model=SentimentResponse)
def predict(req: SentimentRequest):
    if _model is None:
        PREDICTIONS_TOTAL.labels(model="sentiment", status="error").inc()
        raise HTTPException(status_code=503, detail="model not ready")

    start = time.time()
    try:
        proba = _model.predict_proba([req.text])[0]
        label_idx = proba.argmax()
        sentiment = "positive" if label_idx == 1 else "negative"
        confidence = float(proba[label_idx])
        PREDICTIONS_TOTAL.labels(model="sentiment", status="success").inc()
        return SentimentResponse(sentiment=sentiment, confidence=round(confidence, 4))
    except Exception as e:
        PREDICTIONS_TOTAL.labels(model="sentiment", status="error").inc()
        logger.error(f"prediction failed: {e}")
        raise HTTPException(status_code=500, detail="inference failed")
    finally:
        PREDICTION_LATENCY.labels(model="sentiment").observe(time.time() - start)
