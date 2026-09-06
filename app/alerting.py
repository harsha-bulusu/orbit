"""In-process alert evaluator.

Keeps small rolling windows of recent observations per issue — just enough
state to test a threshold, not a time-series database — and fires structured
alerts into app.alert_store when a configured rule is breached.

Thresholds live in app.config.ALERT_RULES; nothing in this module hardcodes a
number that an operator would want to tune.
"""
import threading
import time
from collections import deque

from app.alert_store import alert_store
from app.config import (
    ALERT_COOLDOWN_SECONDS,
    ALERT_RESOLVE_AFTER_SECONDS,
    ALERT_RULES,
    BUG_TOGGLES,
    TIMESERIES_CONFIG,
)

# Raw request events are kept for the chart retention window; alert rules read
# whatever slice of it they need.
_EVENT_RETENTION_SECONDS = (
    TIMESERIES_CONFIG["retention_samples"] * TIMESERIES_CONFIG["sample_interval_seconds"]
)


def _percentile(sorted_values, pct: float) -> float:
    """Nearest-rank percentile. Expects a pre-sorted, non-empty list."""
    if not sorted_values:
        return 0.0
    k = max(0, min(len(sorted_values) - 1, int(round((pct / 100.0) * len(sorted_values) + 0.5)) - 1))
    return sorted_values[k]


class AlertEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._requests = deque()          # (ts, path, status, duration_ms)
        self._batches = deque(maxlen=200)  # (ts, duration_ms, batch_size)
        self._conn_samples = deque(maxlen=64)  # (ts, open_connections)
        self._connections = 0
        self._peak_connections = 0
        # Per-rule alert bookkeeping.
        self._active = {}       # rule_key -> alert_id
        self._last_fired = {}   # rule_key -> monotonic-ish epoch seconds
        self._below_since = {}  # rule_key -> epoch seconds the breach cleared

    # ---------------------------------------------------------------- ingest

    def record_request(self, path: str, status: int, duration_ms: float) -> None:
        now = time.time()
        with self._lock:
            self._requests.append((now, path, status, duration_ms))
            cutoff = now - _EVENT_RETENTION_SECONDS
            while self._requests and self._requests[0][0] < cutoff:
                self._requests.popleft()
        self.evaluate()

    def record_batch(self, duration_ms: float, batch_size: int) -> None:
        with self._lock:
            self._batches.append((time.time(), duration_ms, batch_size))
        self.evaluate()

    def record_connection_delta(self, delta: int) -> None:
        """Mirrors the open_db_connections_total UpDownCounter.

        OTel instruments are write-only, so the engine keeps its own copy of the
        value in order to evaluate a threshold against it.
        """
        with self._lock:
            self._connections = max(0, self._connections + delta)
            self._peak_connections = max(self._peak_connections, self._connections)

    def sample_gauges(self) -> None:
        """Called once per tick so the connection gauge has an evenly spaced series."""
        with self._lock:
            self._conn_samples.append((time.time(), self._connections))

    # ------------------------------------------------------------- read-side

    def _requests_since(self, seconds: float):
        cutoff = time.time() - seconds
        return [r for r in self._requests if r[0] >= cutoff]

    def error_count(self, path: str, min_status: int, window_seconds: float) -> int:
        with self._lock:
            return sum(
                1
                for _, p, status, _ in self._requests_since(window_seconds)
                if p == path and status >= min_status
            )

    def batch_percentile(self, pct: float, sample_count: int, max_age_seconds: float = None):
        cutoff = time.time() - max_age_seconds if max_age_seconds else None
        with self._lock:
            recent = list(self._batches)[-sample_count:]
        samples = [d for ts, d, _ in recent if cutoff is None or ts >= cutoff]
        if not samples:
            return None, 0
        return _percentile(sorted(samples), pct), len(samples)

    def connection_trend(self, sample_count: int):
        """Returns (current, n, rising, non_decreasing) over the last N gauge samples.

        `non_decreasing` is the leak signal: a healthy pool returns connections
        between requests, so its series comes back down. A leaked pool either
        climbs or plateaus at its high-water mark — it never drains.
        """
        with self._lock:
            values = [v for _, v in list(self._conn_samples)[-sample_count:]]
            current = self._connections
        if len(values) < 2:
            return current, len(values), False, False
        non_decreasing = all(b >= a for a, b in zip(values, values[1:]))
        return current, len(values), non_decreasing and values[-1] > values[0], non_decreasing

    def traffic_snapshot(self, window_seconds: float) -> dict:
        """Rates and latency percentiles over a trailing window, for the charts."""
        with self._lock:
            events = self._requests_since(window_seconds)
        total = len(events)
        errors = [e for e in events if e[2] >= 400]
        server_errors = [e for e in events if e[2] >= 500]
        durations = sorted(e[3] for e in events)
        by_path = {}
        for _, path, status, _ in errors:
            by_path[path] = by_path.get(path, 0) + 1
        return {
            "requests_per_sec": round(total / window_seconds, 3),
            "errors_per_sec": round(len(errors) / window_seconds, 3),
            "server_errors_per_sec": round(len(server_errors) / window_seconds, 3),
            "error_ratio": round(len(errors) / total, 4) if total else 0.0,
            "p50_ms": round(_percentile(durations, 50), 2) if durations else 0.0,
            "p95_ms": round(_percentile(durations, 95), 2) if durations else 0.0,
            "p99_ms": round(_percentile(durations, 99), 2) if durations else 0.0,
            "errors_by_path": by_path,
        }

    def metric_snapshot(self) -> dict:
        """Every metric an alert might reference, captured at fire time."""
        r1 = ALERT_RULES["id_race_condition"]
        r2 = ALERT_RULES["notification_fake_parallel"]
        r3 = ALERT_RULES["unmanaged_connections"]
        p95, batch_n = self.batch_percentile(
            r2["percentile"], r2["sample_count"], r2.get("max_age_seconds")
        )
        current_conns, conn_n, rising, holding = self.connection_trend(r3["sample_count"])
        traffic = self.traffic_snapshot(TIMESERIES_CONFIG["rate_window_seconds"])
        with self._lock:
            recent_batches = [
                {"duration_ms": round(d, 2), "batch_size": n} for _, d, n in list(self._batches)[-5:]
            ]
            conn_series = [v for _, v in list(self._conn_samples)[-r3["sample_count"]:]]
            peak_conns = self._peak_connections
        return {
            "orders_errors_60s": self.error_count(
                r1["path"], r1["min_status"], r1["window_seconds"]
            ),
            "notification_batch_p95_ms": round(p95, 2) if p95 is not None else None,
            "notification_batch_samples": batch_n,
            "recent_batches": recent_batches,
            "open_db_connections_total": current_conns,
            "open_db_connections_peak": peak_conns,
            "open_db_connections_series": conn_series,
            "open_db_connections_rising": rising,
            "open_db_connections_not_draining": holding,
            "open_db_connections_samples": conn_n,
            "traffic": traffic,
            "bug_toggles": dict(BUG_TOGGLES),
        }

    # ------------------------------------------------------------- evaluate

    def _rule_value(self, key: str, rule: dict):
        """Returns (value, breached, has_enough_data) for one rule."""
        kind = rule["kind"]
        if kind == "error_count":
            value = self.error_count(rule["path"], rule["min_status"], rule["window_seconds"])
            return value, value >= rule["threshold"], True

        if kind == "percentile":
            value, n = self.batch_percentile(
                rule["percentile"], rule["sample_count"], rule.get("max_age_seconds")
            )
            if value is None or n < rule.get("min_samples", 1):
                return value, False, False
            return value, value >= rule["threshold"], True

        if kind == "gauge_with_trend":
            value, n, _rising, non_decreasing = self.connection_trend(rule["sample_count"])
            if n < rule.get("min_samples", 1):
                return value, False, False
            breached = value >= rule["threshold"]
            if rule.get("require_rising_trend"):
                breached = breached and non_decreasing
            return value, breached, True

        raise ValueError(f"Unknown alert rule kind: {kind}")

    @staticmethod
    def _window_label(rule: dict) -> str:
        if rule["kind"] == "error_count":
            return f"{rule['window_seconds']}s"
        if rule.get("max_age_seconds"):
            return f"last {rule['sample_count']} samples / {rule['max_age_seconds']}s"
        return f"last {rule['sample_count']} samples"

    def evaluate(self) -> None:
        now = time.time()
        for key, rule in ALERT_RULES.items():
            try:
                value, breached, ready = self._rule_value(key, rule)
            except Exception:  # a broken rule must never take down a request
                continue

            active_id = self._active.get(key)

            if breached and ready:
                self._below_since.pop(key, None)
                if active_id:
                    alert_store.observe(active_id, value)
                    continue
                cooldown = rule.get("cooldown_seconds", ALERT_COOLDOWN_SECONDS)
                if now - self._last_fired.get(key, 0) < cooldown:
                    continue
                alert = alert_store.fire(
                    issue_type=rule["issue_type"],
                    metric_name=rule["metric_name"],
                    current_value=value,
                    threshold=rule["threshold"],
                    window=self._window_label(rule),
                    severity=rule["severity"],
                    service=rule["service"],
                    title=rule["title"],
                    description=rule["description"],
                    unit=rule["unit"],
                    snapshot=self.metric_snapshot(),
                )
                self._active[key] = alert["alert_id"]
                self._last_fired[key] = now
                continue

            # Not breached: hold the alert open until it has been clear long enough.
            if active_id:
                alert_store.observe(active_id, value if value is not None else 0)
                since = self._below_since.setdefault(key, now)
                resolve_after = rule.get("resolve_after_seconds", ALERT_RESOLVE_AFTER_SECONDS)
                if now - since >= resolve_after:
                    alert_store.resolve(active_id, value if value is not None else 0)
                    self._active.pop(key, None)
                    self._below_since.pop(key, None)

    # ---------------------------------------------------------------- status

    def issue_status(self) -> list:
        rows = []
        for key, rule in ALERT_RULES.items():
            value, breached, ready = self._rule_value(key, rule)
            active = alert_store.active_for(rule["issue_type"])
            rows.append({
                "issue_type": rule["issue_type"],
                "title": rule["title"],
                "service": rule["service"],
                "bug_enabled": BUG_TOGGLES.get(key, False),
                "metric_name": rule["metric_name"],
                "current_value": round(value, 2) if isinstance(value, float) else value,
                "threshold": rule["threshold"],
                "unit": rule["unit"],
                "window": self._window_label(rule),
                "severity": rule["severity"],
                "breaching": bool(breached and ready),
                "has_data": ready,
                "active_alert_id": active["alert_id"] if active else None,
                "active_alert_since": active["triggered_at"] if active else None,
            })
        return rows

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._batches.clear()
            self._conn_samples.clear()
            self._connections = 0
            self._peak_connections = 0
        self._active.clear()
        self._last_fired.clear()
        self._below_since.clear()


engine = AlertEngine()
