import os
import subprocess
import sys
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.alert_store import alert_store
from app.alerting import engine
from app.config import BUG_TOGGLES
from app.db import SessionLocal
from app.models import Order, Product, Review
from app.seed_data import seed_products
from app.timeseries import buffer

router = APIRouter(prefix="/admin")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bug toggle -> scripts/load_test.py --issue N
ISSUE_NUMBERS = {
    "id_race_condition": 1,
    "notification_fake_parallel": 2,
    "unmanaged_connections": 3,
}

_runs_lock = threading.Lock()
_runs = {}  # issue -> {status, started_at, finished_at, exit_code, output}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/bugs")
def get_bugs():
    return BUG_TOGGLES


@router.post("/bugs/{name}/enable")
def enable_bug(name: str):
    if name not in BUG_TOGGLES:
        raise HTTPException(status_code=404, detail=f"Unknown bug toggle: {name}")
    BUG_TOGGLES[name] = True
    return {name: True}


@router.post("/bugs/{name}/disable")
def disable_bug(name: str):
    if name not in BUG_TOGGLES:
        raise HTTPException(status_code=404, detail=f"Unknown bug toggle: {name}")
    BUG_TOGGLES[name] = False

    released = None
    if name == "unmanaged_connections":
        # Connections already leaked would keep the saturation gauge pinned
        # above threshold forever; handing them back models the fix actually
        # shipping, so the alert can drop below threshold and auto-resolve.
        from app.services.connection_service import release_leaked_connections

        released = release_leaked_connections()

    response = {name: False}
    if released is not None:
        response["connections_released"] = released
    return response


def _run_load_test(issue_key: str, issue_number: int, n: int = None):
    cmd = [sys.executable, "-m", "scripts.load_test", "--issue", str(issue_number)]
    if n:
        cmd += ["--n", str(n)]
    try:
        proc = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=180
        )
        result = {
            "status": "finished" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
            "output": (proc.stdout + proc.stderr).strip()[-4000:],
        }
    except Exception as exc:
        result = {"status": "failed", "exit_code": None, "output": f"{type(exc).__name__}: {exc}"}
    with _runs_lock:
        _runs[issue_key].update(result, finished_at=_now_iso())


@router.post("/trigger-load/{issue}")
def trigger_load(issue: str, n: int = None):
    """Runs the matching scripts/load_test.py scenario in a subprocess.

    A subprocess (rather than an in-process call) is what keeps this from
    deadlocking: the script drives load against this same server, so it has to
    run outside the event loop that must answer it.
    """
    if issue not in ISSUE_NUMBERS:
        raise HTTPException(status_code=404, detail=f"Unknown issue: {issue}")

    with _runs_lock:
        existing = _runs.get(issue)
        if existing and existing["status"] == "running":
            return {"issue": issue, **existing}
        _runs[issue] = {
            "status": "running",
            "started_at": _now_iso(),
            "finished_at": None,
            "exit_code": None,
            "output": "",
        }

    threading.Thread(
        target=_run_load_test, args=(issue, ISSUE_NUMBERS[issue], n), daemon=True
    ).start()

    with _runs_lock:
        return {"issue": issue, **_runs[issue]}


@router.get("/trigger-load")
def load_runs():
    with _runs_lock:
        return {"runs": {k: dict(v) for k, v in _runs.items()}}


@router.post("/reset")
def reset():
    db = SessionLocal()
    try:
        db.query(Order).delete()
        db.query(Review).delete()
        db.query(Product).delete()
        db.commit()
    finally:
        db.close()

    seed_products()

    from app.services.connection_service import release_leaked_connections

    released = release_leaked_connections()
    engine.reset()
    alert_store.clear()
    buffer.clear()
    with _runs_lock:
        _runs.clear()

    return {"status": "reset", "connections_released": released}
