import json
import os
import threading

from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
TRACE_FILE = os.path.join(LOG_DIR, "traces.jsonl")

_configured = False
_file_lock = threading.Lock()


class FileSpanExporter(SpanExporter):
    """Writes one JSON object per completed span to a .jsonl file. No collector involved."""

    def __init__(self, path: str):
        self._path = path

    def export(self, spans):
        with _file_lock, open(self._path, "a") as f:
            for span in spans:
                ctx = span.get_span_context()
                parent = span.parent
                record = {
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                    "parent_span_id": format(parent.span_id, "016x") if parent else None,
                    "name": span.name,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": (span.end_time - span.start_time) / 1_000_000,
                    "attributes": dict(span.attributes or {}),
                }
                f.write(json.dumps(record) + "\n")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def setup_tracing(app=None, engine=None):
    global _configured
    if _configured:
        return trace.get_tracer("orbit")

    provider = TracerProvider(resource=Resource.create({"service.name": "orbit"}))
    provider.add_span_processor(SimpleSpanProcessor(FileSpanExporter(TRACE_FILE)))
    trace.set_tracer_provider(provider)

    LoggingInstrumentor().instrument(
        set_logging_format=False,
        inject_trace_context=True,
        enable_log_auto_instrumentation=False,
    )

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)

    if engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=engine)

    _configured = True
    return trace.get_tracer("orbit")


def get_tracer():
    return trace.get_tracer("orbit")
