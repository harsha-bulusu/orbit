import time

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.order_service import create_order
from app.telemetry.logging_setup import get_logger
from app.telemetry.metrics_setup import get_instruments

router = APIRouter()
logger = get_logger(__name__)


class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int = 1


@router.post("/orders", status_code=201)
def post_order(payload: OrderCreate, db: Session = Depends(get_db)):
    start = time.perf_counter()
    try:
        order = create_order(db, payload.user_id, payload.product_id, payload.quantity)
    except IntegrityError as exc:
        db.rollback()
        span = trace.get_current_span()
        span.set_attribute("error_type", "IntegrityError")
        span.record_exception(exc)
        instruments = get_instruments()
        if instruments:
            instruments["order_creation_conflicts_total"].add(1)
        latency_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "order_creation_failed",
            extra={
                "event": "order_creation_failed",
                "endpoint": "/orders",
                "status": 409,
                "latency_ms": latency_ms,
                "error_type": "IntegrityError",
            },
        )
        raise HTTPException(status_code=409, detail="Order ID collision") from exc

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "order_created",
        extra={
            "event": "order_created",
            "endpoint": "/orders",
            "status": 201,
            "latency_ms": latency_ms,
        },
    )
    return {"id": order.id, "user_id": order.user_id, "product_id": order.product_id, "quantity": order.quantity}
