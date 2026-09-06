from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource

_configured = False
_instruments = {}


def setup_metrics():
    global _configured
    if _configured:
        return _instruments

    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=Resource.create({"service.name": "orbit"}), metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("orbit")

    _instruments["http_requests_total"] = meter.create_counter(
        "http_requests_total", description="Total HTTP requests"
    )
    _instruments["http_request_duration_seconds"] = meter.create_histogram(
        "http_request_duration_seconds", description="HTTP request duration", unit="s"
    )
    # UpDownCounter renders as a Prometheus gauge — lets us show it climb (buggy)
    # or plateau (fixed) as connections open/close.
    _instruments["open_db_connections_total"] = meter.create_up_down_counter(
        "open_db_connections_total", description="Currently open DB connections"
    )
    _instruments["notification_batch_duration_seconds"] = meter.create_histogram(
        "notification_batch_duration_seconds", description="Notification batch processing duration", unit="s"
    )
    _instruments["order_creation_conflicts_total"] = meter.create_counter(
        "order_creation_conflicts_total", description="Order ID collision conflicts"
    )

    _configured = True
    return _instruments


def get_instruments():
    return _instruments
