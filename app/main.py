import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app import admin
from app.alerting import engine as alert_engine
from app.db import Base, engine
from app.routes import alerts, notifications, orders, products
from app.telemetry.logging_setup import setup_logging
from app.telemetry.metrics_setup import setup_metrics
from app.telemetry.tracing_setup import setup_tracing
from app.timeseries import start_sampler

setup_logging()
instruments = setup_metrics()

app = FastAPI(title="Orbit")
setup_tracing(app=app, engine=engine)

# The dashboard runs on the Vite dev server during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def _start_background_sampler():
    start_sampler()


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    path = request.url.path
    instruments["http_requests_total"].add(1, {"method": request.method, "path": path, "status": str(response.status_code)})
    instruments["http_request_duration_seconds"].record(duration, {"method": request.method, "path": path})
    # Dashboard polling would otherwise dominate the traffic/latency charts.
    if not path.startswith(("/metrics", "/alerts", "/health", "/admin")):
        alert_engine.record_request(path, response.status_code, duration * 1000)
    return response


# Registered before the /metrics mount so GET /metrics/timeseries resolves to
# the exact route rather than the Prometheus ASGI app's prefix match.
app.include_router(alerts.router)
app.include_router(orders.router)
app.include_router(notifications.router)
app.include_router(products.router)
app.include_router(admin.router)

app.mount("/metrics", make_asgi_app())
