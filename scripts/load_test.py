"""Fires the concurrency/volume pattern for one of the three demo issues.

Usage:
    python -m scripts.load_test --issue 1
    python -m scripts.load_test --issue 2
    python -m scripts.load_test --issue 3
"""
import argparse
import asyncio
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def run_issue_1(client: httpx.AsyncClient, n: int):
    print(f"Issue 1: firing {n} concurrent POST /orders")
    tasks = [client.post("/orders", json={"user_id": 1, "product_id": 1, "quantity": 1}) for _ in range(n)]

    start = time.perf_counter()
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.perf_counter() - start

    statuses = {}
    for r in responses:
        key = "client_error" if isinstance(r, Exception) else r.status_code
        statuses[key] = statuses.get(key, 0) + 1

    print(f"Done in {duration:.2f}s. Status breakdown: {statuses}")
    if statuses.get(409):
        print(f"BUG CONFIRMED: {statuses[409]} order ID collisions (409 IntegrityError).")
    else:
        print("No collisions observed.")


async def run_issue_2(client: httpx.AsyncClient, batches: int):
    """Sends `batches` batches of 4 messages, so the p95 alert rule has samples.

    A single batch is enough to eyeball the trace, but a percentile rule needs
    a handful of observations before it will evaluate.
    """
    print(f"Issue 2: sending {batches} batches of 4 messages with matching cost")
    messages = [{"id": i, "cost_ms": 300} for i in range(1, 5)]

    durations = []
    for n in range(batches):
        start = time.perf_counter()
        resp = await client.post("/notifications/process-batch", json={"messages": messages})
        duration = time.perf_counter() - start
        durations.append(duration)
        print(f"  batch {n + 1}/{batches}: status {resp.status_code}, wall time {duration:.2f}s")

    worst = max(durations)
    print(f"Slowest batch: {worst:.2f}s")
    if worst > 1.0:
        print("BUG LIKELY: wall time ~= sum of per-message costs -> serialized processing.")
    else:
        print("Looks parallel: wall time ~= a single message's cost.")
    print("Inspect logs/traces.jsonl for 'process_message' span timestamp overlap.")


async def run_issue_3(client: httpx.AsyncClient, n: int, delay: float):
    print(f"Issue 3: firing {n} sequential GET /products to accumulate open connections")
    statuses = {}
    for _ in range(n):
        r = await client.get("/products")
        statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
        # Paced so the gauge climb spans several 1s samples instead of landing
        # as a single vertical step on the saturation chart.
        if delay:
            await asyncio.sleep(delay)

    print("Firing one request with simulate_error=true to test cleanup-on-exception")
    r = await client.get("/products", params={"simulate_error": "true"})
    statuses[r.status_code] = statuses.get(r.status_code, 0) + 1

    print(f"Status breakdown: {statuses}")
    print("Check GET /metrics for open_db_connections_total — climbing means buggy, plateaued means fixed.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, required=True, choices=[1, 2, 3])
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--batches", type=int, default=6, help="issue 2: how many batches to send")
    parser.add_argument("--delay", type=float, default=0.12, help="issue 3: seconds between requests")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        if args.issue == 1:
            await run_issue_1(client, n=args.n or 20)
        elif args.issue == 2:
            await run_issue_2(client, batches=args.batches)
        elif args.issue == 3:
            await run_issue_3(client, n=args.n or 50, delay=args.delay)


if __name__ == "__main__":
    asyncio.run(main())
