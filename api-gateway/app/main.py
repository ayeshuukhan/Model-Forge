import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.database.session import engine
from app.database.models import Base
from app.routes import health, models, predict, inference
from app.metrics import HTTP_REQUESTS

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","service":"api-gateway","level":"%(levelname)s","event":"%(message)s"}',
)
logger = logging.getLogger("api-gateway")

app = FastAPI(title="ModelForge API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # In production you would use Alembic migrations instead of create_all.
    # create_all is kept as a safety net for first-run local/dev environments.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("database tables ensured")
    except Exception as e:
        logger.error(f"failed to initialize database: {e}")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    HTTP_REQUESTS.labels(
        method=request.method, path=request.url.path, status_code=response.status_code
    ).inc()
    duration = time.time() - start
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.3f}s")
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health.router)
app.include_router(models.router)
app.include_router(predict.router)
app.include_router(inference.router)
