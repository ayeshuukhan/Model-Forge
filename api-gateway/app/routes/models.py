from fastapi import APIRouter

router = APIRouter()

AVAILABLE_MODELS = [
    {"name": "sentiment", "type": "text-classification", "description": "Positive/negative sentiment analysis"},
    {"name": "image", "type": "image-classification", "description": "Lightweight image classifier (cat/dog/other)"},
    {"name": "regression", "type": "regression", "description": "House price regression from tabular features"},
]


@router.get("/api/v1/models")
def list_models():
    return {"models": AVAILABLE_MODELS}
