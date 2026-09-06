from fastapi import APIRouter, HTTPException, Query

from app.alert_store import alert_store
from app.alerting import engine
from app.config import ALERT_COOLDOWN_SECONDS, ALERT_RESOLVE_AFTER_SECONDS, ALERT_RULES
from app.timeseries import buffer

router = APIRouter()


@router.get("/alerts")
def list_alerts(
    limit: int = Query(100, ge=1, le=500),
    status: str = Query(None, pattern="^(active|resolved)$"),
    issue_type: str = None,
):
    return {
        "alerts": alert_store.list(limit=limit, status=status, issue_type=issue_type),
        "counts": alert_store.counts(),
    }


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    alert = alert_store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Unknown alert: {alert_id}")
    return alert


@router.get("/health/issues")
def health_issues():
    issues = engine.issue_status()
    return {
        "issues": issues,
        "counts": alert_store.counts(),
        "config": {
            "cooldown_seconds": ALERT_COOLDOWN_SECONDS,
            "resolve_after_seconds": ALERT_RESOLVE_AFTER_SECONDS,
        },
    }


@router.get("/alerts/rules/config")
def alert_rules():
    return {"rules": ALERT_RULES}


@router.get("/metrics/timeseries")
def metrics_timeseries(limit: int = Query(180, ge=1, le=600)):
    """Pre-aggregated rates/percentiles for the charts.

    Registered ahead of the /metrics Prometheus mount in app/main.py so this
    exact path wins over the mount's prefix match.
    """
    return {
        "series": buffer.series(limit=limit),
        "thresholds": {
            "open_connections": ALERT_RULES["unmanaged_connections"]["threshold"],
            "batch_p95_ms": ALERT_RULES["notification_fake_parallel"]["threshold"],
            "orders_errors_60s": ALERT_RULES["id_race_condition"]["threshold"],
        },
    }
