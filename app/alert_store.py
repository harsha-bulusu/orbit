"""Append-only in-memory alert log, queryable by the dashboard UI.

Deliberately not persisted: the demo resets with the process, and keeping it in
memory avoids a second storage dependency alongside orbit.db.
"""
import threading
import uuid
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlertStore:
    def __init__(self, max_alerts: int = 500):
        self._alerts = []
        self._lock = threading.Lock()
        self._max_alerts = max_alerts

    def fire(
        self,
        *,
        issue_type: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        window: str,
        severity: str,
        service: str,
        title: str,
        description: str,
        unit: str,
        snapshot: dict,
    ) -> dict:
        alert = {
            "alert_id": uuid.uuid4().hex[:12],
            "issue_type": issue_type,
            "triggered_at": _now_iso(),
            "resolved_at": None,
            "metric_name": metric_name,
            "current_value": current_value,
            "peak_value": current_value,
            "threshold": threshold,
            "window": window,
            "severity": severity,
            "service": service,
            "status": "active",
            "title": title,
            "description": description,
            "unit": unit,
            "snapshot": snapshot,
        }
        with self._lock:
            self._alerts.append(alert)
            if len(self._alerts) > self._max_alerts:
                del self._alerts[: len(self._alerts) - self._max_alerts]
        return alert

    def observe(self, alert_id: str, value: float) -> None:
        """Track the worst value seen while an alert is still active."""
        with self._lock:
            for alert in self._alerts:
                if alert["alert_id"] == alert_id and alert["status"] == "active":
                    alert["current_value"] = value
                    if value > alert["peak_value"]:
                        alert["peak_value"] = value
                    return

    def resolve(self, alert_id: str, final_value: float) -> None:
        with self._lock:
            for alert in self._alerts:
                if alert["alert_id"] == alert_id and alert["status"] == "active":
                    alert["status"] = "resolved"
                    alert["resolved_at"] = _now_iso()
                    alert["current_value"] = final_value
                    return

    def active_for(self, issue_type: str):
        with self._lock:
            for alert in reversed(self._alerts):
                if alert["issue_type"] == issue_type and alert["status"] == "active":
                    return dict(alert)
        return None

    def list(self, limit: int = 100, status: str = None, issue_type: str = None):
        with self._lock:
            items = list(reversed(self._alerts))
        if status:
            items = [a for a in items if a["status"] == status]
        if issue_type:
            items = [a for a in items if a["issue_type"] == issue_type]
        # Summary view: the full metric snapshot is only served by /alerts/{id}.
        return [{k: v for k, v in a.items() if k != "snapshot"} for a in items[:limit]]

    def get(self, alert_id: str):
        with self._lock:
            for alert in self._alerts:
                if alert["alert_id"] == alert_id:
                    return dict(alert)
        return None

    def counts(self) -> dict:
        with self._lock:
            active = sum(1 for a in self._alerts if a["status"] == "active")
            return {"total": len(self._alerts), "active": active, "resolved": len(self._alerts) - active}

    def clear(self) -> None:
        with self._lock:
            self._alerts.clear()


alert_store = AlertStore()
