# Orbit

A small e-commerce demo API (FastAPI + SQLAlchemy/SQLite) instrumented with
OpenTelemetry logs, traces, and metrics, wired with three independently
toggleable bugs, an **in-process alerting engine**, and a **React monitoring
dashboard**.

## Setup

### API

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`. Logs land in `logs/app.log`
(JSON-lines), spans in `logs/traces.jsonl` (JSON-lines), and Prometheus
metrics are served at `GET /metrics`.

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies every API path to
`127.0.0.1:8000`, so the dashboard is same-origin and needs no configuration.
It polls `/metrics/timeseries`, `/alerts`, and `/health/issues` every 3s.

## Bug toggles

```
GET  /admin/bugs
POST /admin/bugs/{name}/enable
POST /admin/bugs/{name}/disable
POST /admin/trigger-load/{name}   # runs scripts/load_test.py server-side
GET  /admin/trigger-load          # status + stdout of the last run per issue
POST /admin/reset                 # clears orders, reseeds, releases leaked
                                  # connections, clears alerts + metric windows
```

Toggle names: `id_race_condition`, `notification_fake_parallel`, `unmanaged_connections`.

Disabling `unmanaged_connections` also releases the already-leaked connections.
Without that, the saturation gauge would stay pinned above threshold forever and
its alert could never auto-resolve — the release models the fix actually shipping.

## The three issues

| # | Toggle | Endpoint | Signal |
|---|---|---|---|
| 1 | `id_race_condition` | `POST /orders` | `order_creation_conflicts_total` counter, `409` responses, `IntegrityError` in logs/spans |
| 2 | `notification_fake_parallel` | `POST /notifications/process-batch` | `process_message` spans in `traces.jsonl` — sequential (non-overlapping) vs. parallel (overlapping) timestamps |
| 3 | `unmanaged_connections` | `GET /products` | `open_db_connections_total` gauge climbs (buggy) vs. plateaus (fixed) |

## Alerting

`app/alerting.py` is an in-process evaluator — no Prometheus, no Alertmanager,
no external delivery. It keeps a small rolling window per issue (just enough
state to test a threshold, not a time-series store) and fires structured alerts
into the append-only log in `app/alert_store.py`.

Thresholds are config, not code: they live in `ALERT_RULES` in `app/config.py`
alongside the bug toggles, so they are tunable without touching the evaluator.

| Rule kind | Issue | What it watches |
|---|---|---|
| `error_count` | 1 | non-2xx responses on `/orders` in a rolling 60s window (`/orders` answers a collision with 409, so the rule counts `>= 400`; raise `min_status` to 500 for server errors only) |
| `percentile` | 2 | p95 batch-processing latency over the last 20 batches, capped at 60s of age |
| `gauge_with_trend` | 3 | open-connection gauge above its ceiling **and** never draining across the last 10 one-second samples |

Firing an alert captures a full metric snapshot; a per-rule cooldown (default
120s) stops a sustained breach from refiring; an alert auto-resolves once its
metric has been back below threshold for a sustained period (default 30s). A
background 1s sampler drives both the chart series and the resolve checks, so an
alert clears even after load stops entirely.

### Read endpoints

```
GET /alerts                  # most recent first, ?status=active|resolved, ?issue_type=
GET /alerts/{alert_id}       # full detail incl. the metric snapshot at fire time
GET /alerts/rules/config     # the configured thresholds
GET /health/issues           # all three toggles + current value vs threshold + active alert
GET /metrics/timeseries      # pre-aggregated rates/percentiles for the charts
```

`/metrics/timeseries` exists so the browser doesn't have to re-derive rates and
percentiles from cumulative Prometheus counters. Its route is registered ahead
of the `/metrics` mount in `app/main.py` so the exact path wins over the mount's
prefix match. Dashboard polling traffic is excluded from the request series.

## Dashboard

React + Vite, Tailwind, Apache ECharts. Three screens:

- **Overview** — a status card per issue, then the golden signals: traffic
  (req/s), errors (err/s split by endpoint), latency (p50/p95/p99), saturation
  (open connections, with a reference line at the configured threshold), and the
  Issue-2 alert metric (batch p95, with its own reference line).
- **Alerts** — the alert log, most recent first; a row expands to the metric
  snapshot captured at fire time. Active vs. resolved is carried by a solid vs.
  hollow dot, not a wall of red.
- **Console** — bug toggles, per-issue "trigger load", the load run's stdout,
  and reset.

The palette is three hues and no more: a neutral slate ramp, one accent
(`#3d9ae8`), one status color (`#e0575b`) reserved for error/critical state.
p50/p95/p99 are one hue at three weights — series are distinguished by opacity
and dash pattern, never by adding a color.

## Demo flow (per issue)

From the dashboard's Console tab: toggle the bug on, click **trigger load**,
watch the chart shape change and the alert appear, then toggle the bug off and
click **trigger load** again to watch it auto-resolve.

Equivalently from a shell:

```bash
curl -X POST http://127.0.0.1:8000/admin/bugs/id_race_condition/enable
python -m scripts.load_test --issue 1
curl -s http://127.0.0.1:8000/alerts | python -m json.tool
curl -X POST http://127.0.0.1:8000/admin/bugs/id_race_condition/disable
python -m scripts.load_test --issue 1   # re-verify; the alert resolves ~30s later
```

Repeat with `--issue 2` / `notification_fake_parallel` and `--issue 3` /
`unmanaged_connections`.

`scripts/load_test.py` takes `--batches` (issue 2, default 6 — a percentile rule
needs more than one observation) and `--delay` (issue 3, default 0.12s between
requests, so the gauge climb spans several one-second samples instead of landing
as a single vertical step).
# orbit
