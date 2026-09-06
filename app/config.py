"""Bug toggles, simulation knobs, and alert threshold rules.

Alert *logic* lives in app/alerting.py; the numbers it compares against live
here so thresholds are tunable without touching the evaluator.
"""

BUG_TOGGLES = {
    "id_race_condition": False,
    "notification_fake_parallel": False,
    "unmanaged_connections": False,
}

SIM_CONFIG = {
    "notification_batch_size": 4,
    "order_race_window_ms": 10,
}

# How long a fired alert stays quiet before the same rule may fire again.
ALERT_COOLDOWN_SECONDS = 120
# How long the metric must sit back below threshold before an alert auto-resolves.
ALERT_RESOLVE_AFTER_SECONDS = 30

# One rule per demo issue. `kind` selects the evaluator in app/alerting.py.
#   error_count      -> count of error responses on `path` within `window_seconds`
#   percentile       -> `percentile` of the last `sample_count` observations
#   gauge_with_trend -> current gauge value, optionally requiring a rising trend
ALERT_RULES = {
    "id_race_condition": {
        "kind": "error_count",
        "issue_type": "id_race_condition",
        "title": "Order creation error rate elevated",
        "service": "order-service",
        "metric_name": "orders_errors_60s",
        "unit": "errors",
        "path": "/orders",
        # /orders answers an ID collision with 409, so the rule counts every
        # non-2xx rather than 5xx only; raise to 500 to watch server errors only.
        "min_status": 400,
        "window_seconds": 60,
        "threshold": 5,
        "severity": "critical",
        "description": "Concurrent POST /orders requests are failing. Expect duplicate-ID IntegrityErrors from the order service.",
    },
    "notification_fake_parallel": {
        "kind": "percentile",
        "issue_type": "notification_fake_parallel",
        "title": "Notification batch p95 latency breach",
        "service": "notification-service",
        "metric_name": "notification_batch_p95_ms",
        "unit": "ms",
        "percentile": 95,
        "sample_count": 20,
        # Bounded by age as well as count: a purely count-based window would
        # keep a breach alive indefinitely once traffic stops, since the old
        # slow samples would never be pushed out.
        "max_age_seconds": 60,
        "min_samples": 3,
        "threshold": 800,
        "severity": "warning",
        "description": "Batch processing latency is scaling with batch size — work that should run in parallel is being serialized.",
    },
    "unmanaged_connections": {
        "kind": "gauge_with_trend",
        "issue_type": "unmanaged_connections",
        "title": "Open DB connections above ceiling",
        "service": "product-service",
        "metric_name": "open_db_connections_total",
        "unit": "connections",
        "sample_count": 10,
        "min_samples": 5,
        # Both must hold: over the ceiling AND the series never comes back
        # down across the window (a healthy pool drains between requests).
        "require_rising_trend": True,
        "threshold": 25,
        "severity": "critical",
        "description": "Open connection count is climbing monotonically with request volume — connections are not being returned to the pool.",
    },
}

# Rolling series kept in memory for the dashboard charts.
TIMESERIES_CONFIG = {
    "sample_interval_seconds": 1.0,
    "retention_samples": 300,   # 5 minutes at 1s resolution
    "rate_window_seconds": 5.0,  # trailing window used to smooth rates/percentiles
}
