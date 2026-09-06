import logging
import os

from pythonjsonlogger import jsonlogger

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

_configured = False


def setup_logging():
    global _configured
    if _configured:
        return
    handler = logging.FileHandler(LOG_FILE)
    # otelTraceID/otelSpanID are injected onto every LogRecord by OTel's
    # LoggingInstrumentor once it's instrumented in tracing_setup.py.
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "otelTraceID": "trace_id",
            "otelSpanID": "span_id",
        },
    )
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    _configured = True


class OrbitLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra.setdefault("service", "orbit")
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> OrbitLoggerAdapter:
    setup_logging()
    return OrbitLoggerAdapter(logging.getLogger(name), {})
