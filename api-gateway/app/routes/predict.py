import time
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import InferenceRequest
from app.services.model_client import call_model_service, MODEL_SERVICES
from app.services.redis_client import publish_inference_event
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, INFERENCE_ERRORS

logger = logging.getLogger("api-gateway")
router = APIRouter()

MAX_JSON_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


@router.post("/api/v1/predict/{model_name}")
async def predict(
    model_name: str,
    request: Request,
    db: Session = Depends(get_db),
    file: UploadFile = File(None),
):
    if model_name not in MODEL_SERVICES:
        raise HTTPException(status_code=404, detail=f"unknown model '{model_name}'")

    inference_id = str(uuid.uuid4())
    record = InferenceRequest(
        id=inference_id,
        model_name=model_name,
        request_status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    start = time.time()
    try:
        if model_name == "image":
            if file is None:
                raise HTTPException(status_code=422, detail="an image file is required for this model")
            contents = await file.read()
            files = {"file": (file.filename, contents, file.content_type)}
            result = await call_model_service(model_name, files=files)
        else:
            body = await request.body()
            if len(body) > MAX_JSON_BODY_BYTES:
                raise HTTPException(status_code=413, detail="request body too large")
            import json
            try:
                payload = json.loads(body) if body else {}
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="malformed JSON body")
            result = await call_model_service(model_name, json_payload=payload)

        latency_ms = (time.time() - start) * 1000

        record.request_status = "success"
        record.completed_at = datetime.utcnow()
        record.latency_ms = latency_ms
        record.prediction = str(result.get("prediction") or result.get("sentiment"))
        record.confidence = result.get("confidence")
        db.commit()

        REQUEST_COUNT.labels(model=model_name, status="success").inc()
        REQUEST_LATENCY.labels(model=model_name).observe(latency_ms / 1000)
        publish_inference_event(inference_id, model_name, "success")

        return {"inference_id": inference_id, **result}

    except HTTPException as e:
        latency_ms = (time.time() - start) * 1000
        record.request_status = "failed"
        record.completed_at = datetime.utcnow()
        record.latency_ms = latency_ms
        record.error_message = str(e.detail)
        db.commit()

        REQUEST_COUNT.labels(model=model_name, status="failed").inc()
        INFERENCE_ERRORS.labels(model=model_name, error_type="client_error").inc()
        publish_inference_event(inference_id, model_name, "failed")
        raise

    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        record.request_status = "failed"
        record.completed_at = datetime.utcnow()
        record.latency_ms = latency_ms
        record.error_message = "internal error"
        db.commit()

        logger.error(f"inference failed for {model_name}: {e}")
        REQUEST_COUNT.labels(model=model_name, status="failed").inc()
        INFERENCE_ERRORS.labels(model=model_name, error_type="server_error").inc()
        publish_inference_event(inference_id, model_name, "failed")

        raise HTTPException(status_code=502, detail="model service unavailable or returned an error")
