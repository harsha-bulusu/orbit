import time

from fastapi import APIRouter

from app.services.connection_service import get_products
from app.telemetry.logging_setup import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/products")
def list_products(simulate_error: bool = False):
    start = time.perf_counter()
    try:
        result = get_products(simulate_error=simulate_error)
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "products_list_failed",
            extra={
                "event": "products_list_failed",
                "endpoint": "/products",
                "status": 500,
                "latency_ms": latency_ms,
                "error_type": type(exc).__name__,
            },
        )
        raise

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "products_listed",
        extra={
            "event": "products_listed",
            "endpoint": "/products",
            "status": 200,
            "latency_ms": latency_ms,
        },
    )
    return result
