import time
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import SIM_CONFIG
from app.services.notification_service import process_batch
from app.telemetry.logging_setup import get_logger

router = APIRouter()
logger = get_logger(__name__)


class Message(BaseModel):
    id: int
    cost_ms: Optional[int] = 100


class BatchRequest(BaseModel):
    messages: Optional[List[Message]] = None


@router.post("/notifications/process-batch")
def process_batch_endpoint(payload: BatchRequest = BatchRequest()):
    start = time.perf_counter()

    if payload.messages:
        messages = [m.dict() for m in payload.messages]
    else:
        batch_size = SIM_CONFIG["notification_batch_size"]
        messages = [{"id": i, "cost_ms": 100} for i in range(1, batch_size + 1)]

    results = process_batch(messages)

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "batch_processed",
        extra={
            "event": "batch_processed",
            "endpoint": "/notifications/process-batch",
            "status": 200,
            "latency_ms": latency_ms,
        },
    )
    return {"processed": len(results), "results": results}
