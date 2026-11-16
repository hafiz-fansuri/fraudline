"""Warm HTTP latency benchmark including validation, explanations and durable audit writes."""

import argparse
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from fraudline.pipeline import ART, write_json


def run(url, requests=60, concurrency=4):
    if not 1 <= requests <= 90 or not 1 <= concurrency <= 8:
        raise ValueError("Use 1–90 requests and 1–8 concurrent clients to respect the demo rate limit")
    with httpx.Client(base_url=url, timeout=30) as client:
        ready = client.get("/ready")
        ready.raise_for_status()
        sample = client.get("/api/samples").json()["transactions"][0]
        for _ in range(5):
            client.post("/predict", json=sample).raise_for_status()

        def one(_):
            start = time.perf_counter()
            response = client.post("/predict", json=sample)
            response.raise_for_status()
            assert response.json()["prediction_id"]
            return (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            times = list(pool.map(one, range(requests)))
        seconds = time.perf_counter() - start
    ordered = sorted(times)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    result = {
        "requests": requests,
        "concurrency": concurrency,
        "p50_ms": statistics.median(times),
        "p95_ms": p95,
        "max_ms": max(times),
        "throughput_per_second": requests / seconds,
        "warm_p95_under_100ms": p95 < 100,
        "model_version": ready.json()["model_version"],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "scope": "Warm HTTP including feature transformation, explanations and audit writes; cold starts excluded",
    }
    write_json(ART / "reports/load-test.json", result)
    return result


if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8013")
    parser.add_argument("--requests", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(run(args.url, args.requests, args.concurrency), indent=2))
