"""Fixed-size rolling series for the dashboard charts.

Parsing Prometheus exposition text in the browser would mean re-deriving rates
and percentiles client-side from cumulative counters; instead a background tick
samples the alert engine once a second and keeps a bounded ring buffer that
GET /metrics/timeseries serves straight to the UI.
"""
import threading
import time
from collections import deque

from app.alerting import engine
from app.config import ALERT_RULES, TIMESERIES_CONFIG

_INTERVAL = TIMESERIES_CONFIG["sample_interval_seconds"]
_RETENTION = TIMESERIES_CONFIG["retention_samples"]
_RATE_WINDOW = TIMESERIES_CONFIG["rate_window_seconds"]


class TimeSeriesBuffer:
    def __init__(self):
        self._samples = deque(maxlen=_RETENTION)
        self._lock = threading.Lock()

    def sample(self) -> dict:
        engine.sample_gauges()
        traffic = engine.traffic_snapshot(_RATE_WINDOW)
        r1 = ALERT_RULES["id_race_condition"]
        r2 = ALERT_RULES["notification_fake_parallel"]
        p95, _ = engine.batch_percentile(r2["percentile"], r2["sample_count"], r2.get("max_age_seconds"))
        conns, _, _, _ = engine.connection_trend(ALERT_RULES["unmanaged_connections"]["sample_count"])
        row = {
            "t": round(time.time() * 1000),
            "requests_per_sec": traffic["requests_per_sec"],
            "errors_per_sec": traffic["errors_per_sec"],
            "server_errors_per_sec": traffic["server_errors_per_sec"],
            "order_errors_per_sec": round(
                traffic["errors_by_path"].get(r1["path"], 0) / _RATE_WINDOW, 3
            ),
            "p50_ms": traffic["p50_ms"],
            "p95_ms": traffic["p95_ms"],
            "p99_ms": traffic["p99_ms"],
            "batch_p95_ms": round(p95, 2) if p95 is not None else 0.0,
            "open_connections": conns,
        }
        with self._lock:
            self._samples.append(row)
        return row

    def series(self, limit: int = None) -> list:
        with self._lock:
            rows = list(self._samples)
        return rows[-limit:] if limit else rows

    def clear(self) -> None:
        with self._lock:
            self._samples.clear()


buffer = TimeSeriesBuffer()
_stop = threading.Event()


def _loop():
    while not _stop.wait(_INTERVAL):
        try:
            buffer.sample()
            # Gauge-backed rules (and every auto-resolve) need a heartbeat, not
            # just request traffic, or an alert would stay active once load stops.
            engine.evaluate()
        except Exception:
            continue


def start_sampler() -> None:
    thread = threading.Thread(target=_loop, name="orbit-timeseries", daemon=True)
    thread.start()


def stop_sampler() -> None:
    _stop.set()
