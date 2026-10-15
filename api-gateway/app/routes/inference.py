from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.database.models import InferenceRequest

router = APIRouter()


@router.get("/api/v1/inference/{inference_id}")
def get_inference(inference_id: str, db: Session = Depends(get_db)):
    record = db.query(InferenceRequest).filter(InferenceRequest.id == inference_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="inference record not found")
    return {
        "id": record.id,
        "model": record.model_name,
        "status": record.request_status,
        "created_at": record.created_at,
        "completed_at": record.completed_at,
        "latency_ms": record.latency_ms,
        "prediction": record.prediction,
        "confidence": record.confidence,
        "error_message": record.error_message,
    }


@router.get("/api/v1/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(InferenceRequest.id)).scalar()
    by_model = (
        db.query(InferenceRequest.model_name, func.count(InferenceRequest.id))
        .group_by(InferenceRequest.model_name)
        .all()
    )
    by_status = (
        db.query(InferenceRequest.request_status, func.count(InferenceRequest.id))
        .group_by(InferenceRequest.request_status)
        .all()
    )
    avg_latency = db.query(func.avg(InferenceRequest.latency_ms)).scalar()

    return {
        "total_requests": total or 0,
        "by_model": {m: c for m, c in by_model},
        "by_status": {s: c for s, c in by_status},
        "average_latency_ms": round(avg_latency, 2) if avg_latency else None,
    }
