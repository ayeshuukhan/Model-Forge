import httpx
from app.config import settings

MODEL_SERVICES = {
    "sentiment": settings.sentiment_service_url,
    "image": settings.image_service_url,
    "regression": settings.regression_service_url,
}


async def call_model_service(model_name: str, json_payload: dict = None, files=None):
    if model_name not in MODEL_SERVICES:
        raise ValueError(f"unknown model: {model_name}")

    base_url = MODEL_SERVICES[model_name]
    async with httpx.AsyncClient(timeout=settings.model_service_timeout) as client:
        if files is not None:
            resp = await client.post(f"{base_url}/predict", files=files)
        else:
            resp = await client.post(f"{base_url}/predict", json=json_payload)
        resp.raise_for_status()
        return resp.json()
