import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class InferenceRequest(Base):
    __tablename__ = "inference_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name = Column(String, nullable=False, index=True)
    request_status = Column(String, nullable=False, default="pending", index=True)  # pending, success, failed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)
    prediction = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
