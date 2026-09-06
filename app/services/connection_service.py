from sqlalchemy import text

from app.alerting import engine as alert_engine
from app.config import BUG_TOGGLES
from app.db import db_session, engine
from app.models import Product
from app.telemetry.metrics_setup import get_instruments

# Buggy connections are intentionally never closed or returned to the pool —
# kept here only so they aren't garbage-collected out from under the demo.
_leaked_connections = []


def _track_connections(delta: int) -> None:
    """Moves both the exported gauge and the alert engine's readable mirror."""
    instruments = get_instruments()
    if instruments:
        instruments["open_db_connections_total"].add(delta)
    alert_engine.record_connection_delta(delta)


def get_products_buggy(simulate_error: bool = False) -> list:
    conn = engine.connect()
    _track_connections(1)
    _leaked_connections.append(conn)

    if simulate_error:
        raise RuntimeError("Simulated mid-handler failure")

    rows = conn.execute(text("SELECT id, name, description, price, stock FROM products")).mappings().all()
    return [dict(r) for r in rows]


def get_products_fixed(simulate_error: bool = False) -> list:
    with db_session() as db:
        rows = db.query(Product).all()
        if simulate_error:
            raise RuntimeError("Simulated mid-handler failure")
        return [
            {"id": p.id, "name": p.name, "description": p.description, "price": p.price, "stock": p.stock}
            for p in rows
        ]


def get_products(simulate_error: bool = False) -> list:
    if BUG_TOGGLES["unmanaged_connections"]:
        return get_products_buggy(simulate_error=simulate_error)
    return get_products_fixed(simulate_error=simulate_error)


def release_leaked_connections() -> int:
    """Hands the leaked connections back so POST /admin/reset returns to baseline."""
    released = 0
    while _leaked_connections:
        conn = _leaked_connections.pop()
        try:
            conn.close()
        except Exception:
            pass
        _track_connections(-1)
        released += 1
    return released
