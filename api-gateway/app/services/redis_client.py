import logging
import redis
from app.config import settings

logger = logging.getLogger("api-gateway")

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def publish_inference_event(inference_id: str, model_name: str, status: str):
    """
    Push a lightweight event onto a Redis list/stream so that any
    downstream worker (e.g. an analytics aggregator, notification
    service, or audit logger) can process inference events
    asynchronously without blocking the request/response cycle.

    We intentionally do NOT route the actual prediction call through
    Redis - that would add latency for zero benefit. Redis is used
    here for the "fire and forget" side-channel of events.
    """
    try:
        redis_client.xadd(
            "inference_events",
            {"inference_id": inference_id, "model": model_name, "status": status},
            maxlen=10000,
            approximate=True,
        )
    except redis.RedisError as e:
        logger.warning(f"failed to publish event to redis: {e}")
