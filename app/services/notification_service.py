import threading
import time
from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context as otel_context
from opentelemetry import trace

from app.alerting import engine as alert_engine
from app.config import BUG_TOGGLES
from app.telemetry.metrics_setup import get_instruments

_shared_lock = threading.Lock()
tracer = trace.get_tracer("orbit")


def _process_message(message: dict) -> dict:
    cost_ms = message.get("cost_ms", 100)
    with tracer.start_as_current_span(
        "process_message", attributes={"message_id": message["id"], "cost_ms": cost_ms}
    ):
        time.sleep(cost_ms / 1000)
    return {"id": message["id"], "status": "processed"}


def _process_message_buggy(message: dict) -> dict:
    cost_ms = message.get("cost_ms", 100)
    # The span wraps only the locked work (not the thread dispatch), so
    # spans reflect when processing actually ran, not when it was queued —
    # otherwise all 4 threads start their span near-simultaneously and the
    # serialization wouldn't be visible in the timestamps.
    with _shared_lock:
        with tracer.start_as_current_span(
            "process_message", attributes={"message_id": message["id"], "cost_ms": cost_ms}
        ):
            time.sleep(cost_ms / 1000)
    return {"id": message["id"], "status": "processed"}


def process_batch(messages: list) -> list:
    instruments = get_instruments()
    worker_fn = _process_message_buggy if BUG_TOGGLES["notification_fake_parallel"] else _process_message

    with tracer.start_as_current_span("process_batch", attributes={"batch_size": len(messages)}):
        parent_ctx = otel_context.get_current()

        def run_with_context(message):
            token = otel_context.attach(parent_ctx)
            try:
                return worker_fn(message)
            finally:
                otel_context.detach(token)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=len(messages) or 1) as pool:
            results = list(pool.map(run_with_context, messages))
        duration = time.perf_counter() - start

    if instruments:
        instruments["notification_batch_duration_seconds"].record(duration, {"batch_size": str(len(messages))})
    alert_engine.record_batch(duration * 1000, len(messages))

    return results
