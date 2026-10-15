from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database.session import SessionLocal
from app.services.redis_client import redis_client

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    checks = {"database": False, "redis": False}

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = True
    except Exception:
        pass

    try:
        redis_client.ping()
        checks["redis"] = True
    except Exception:
        pass

    if not all(checks.values()):
        raise HTTPException(status_code=503, detail={"status": "not ready", "checks": checks})

    return {"status": "ready", "checks": checks}
