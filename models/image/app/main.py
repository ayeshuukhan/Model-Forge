import logging
import time
import os
import io
import joblib
import numpy as np
from PIL import Image, UnidentifiedImageError
from fastapi import FastAPI, HTTPException, UploadFile, File
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO,
                     format='{"timestamp":"%(asctime)s","service":"image-service","level":"%(levelname)s","event":"%(message)s"}')
logger = logging.getLogger("image-service")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model", "image_model.joblib")
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB request size limit

app = FastAPI(title="Image Classification Service")

PREDICTIONS_TOTAL = Counter(
    "model_predictions_total", "Total predictions made", ["model", "status"]
)
PREDICTION_LATENCY = Histogram(
    "inference_latency_seconds", "Prediction latency in seconds", ["model"]
)

_model = None


def extract_features(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    mean_rgb = arr.mean(axis=(0, 1))
    std_rgb = arr.std(axis=(0, 1))
    brightness = arr.mean()
    return np.concatenate([mean_rgb, std_rgb, [brightness]])


@app.on_event("startup")
def load_model():
    global _model
    if not os.path.exists(MODEL_PATH):
        logger.warning("model file not found, training on startup")
        import subprocess
        subprocess.run(["python", os.path.join(os.path.dirname(__file__), "..", "model", "train.py")], check=True)
    _model = joblib.load(MODEL_PATH)
    logger.info("model loaded successfully")


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


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if _model is None:
        PREDICTIONS_TOTAL.labels(model="image-classifier", status="error").inc()
        raise HTTPException(status_code=503, detail="model not ready")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        PREDICTIONS_TOTAL.labels(model="image-classifier", status="error").inc()
        raise HTTPException(status_code=413, detail="image too large (max 5MB)")

    start = time.time()
    try:
        img = Image.open(io.BytesIO(contents))
        features = extract_features(img).reshape(1, -1)
        proba = _model.predict_proba(features)[0]
        classes = _model.classes_
        best_idx = int(np.argmax(proba))
        PREDICTIONS_TOTAL.labels(model="image-classifier", status="success").inc()
        return {
            "model": "image-classifier",
            "prediction": str(classes[best_idx]),
            "confidence": round(float(proba[best_idx]), 4),
        }
    except UnidentifiedImageError:
        PREDICTIONS_TOTAL.labels(model="image-classifier", status="error").inc()
        raise HTTPException(status_code=400, detail="invalid or unsupported image file")
    except Exception as e:
        PREDICTIONS_TOTAL.labels(model="image-classifier", status="error").inc()
        logger.error(f"prediction failed: {e}")
        raise HTTPException(status_code=500, detail="inference failed")
    finally:
        PREDICTION_LATENCY.labels(model="image-classifier").observe(time.time() - start)
