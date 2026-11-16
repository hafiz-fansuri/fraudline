import json
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from fraudline.data import INPUTS, synthetic
from fraudline.model import Model
from fraudline.pipeline import ART, ROOT, records, registry
from fraudline.store import Store


class Transaction(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    transaction_id: str = Field(default="manual", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    amount: float = Field(gt=0, le=1_000_000, strict=True)
    time_offset: int = Field(ge=0, le=10_000_000_000, strict=True)
    product: Literal["W", "C", "R", "H", "S"]
    network: Literal["visa", "mastercard", "american express", "discover", "unknown"]
    card_type: Literal["debit", "credit", "unknown"]
    distance: float | None = Field(default=None, ge=0, le=100_000, strict=True)
    identity_present: StrictBool


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactions: list[Transaction] = Field(min_length=1, max_length=100)


def create_app(model_path=None, database_url=None):
    metrics = CollectorRegistry()
    count = Counter("fraudline_requests_total", "Requests by status", ["status"], registry=metrics)
    latency = Histogram(
        "fraudline_request_seconds",
        "End-to-end request latency including audit write",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1, 5),
        registry=metrics,
    )
    drift_gauge = Gauge("fraudline_data_drift", "Latest scheduled data drift flag", registry=metrics)

    @asynccontextmanager
    async def lifespan(app):
        app.state.error = None
        app.state.model = None
        try:
            version = os.environ.get("MODEL_VERSION") or registry()["champion"]
            path = model_path or ART / "models" / str(version)
            app.state.model = Model(path)
            app.state.store = Store(
                database_url or os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'runtime/events.db'}")
            )
        except (OSError, ValueError, KeyError) as exc:
            app.state.error = str(exc)
        yield
        if hasattr(app.state, "store"):
            app.state.store.engine.dispose()

    app = FastAPI(title="Fraudline", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
    lock = threading.Lock()
    requests = defaultdict(deque)

    @app.middleware("http")
    async def safety(request: Request, call_next):
        start = time.perf_counter()
        if request.method == "POST":
            host = request.client.host if request.client else "local"
            now = time.monotonic()
            with lock:
                # Bound memory for the single-process demo limiter; use a gateway for multi-worker hosting.
                for key in list(requests):
                    if not requests[key] or now - requests[key][-1] > 60:
                        del requests[key]
                queue = requests[host]
                while queue and now - queue[0] > 60:
                    queue.popleft()
                if len(queue) >= 120 or len(requests) > 10000:
                    return JSONResponse({"detail": "Rate limit reached. Try again in a minute."}, 429)
                queue.append(now)
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 65536:
                    return JSONResponse({"detail": "Request body exceeds 64 KiB"}, 413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        try:
            response = await call_next(request)
        except Exception:
            count.labels("500").inc()
            latency.observe(time.perf_counter() - start)
            raise
        elapsed = time.perf_counter() - start
        count.labels(str(response.status_code)).inc()
        latency.observe(elapsed)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    def ready():
        if app.state.model is None:
            raise HTTPException(
                503, "No verified model is loaded. Run the training pipeline and restart the API."
            )
        return app.state.model

    @app.get("/health")
    def health():
        return {"status": "alive"}

    @app.get("/ready")
    def readiness():
        model = ready()
        return {
            "status": "ready",
            "model_version": model.meta["version"],
            "data_source": model.meta["data_source"],
            "audit_storage": "ephemeral" if os.environ.get("VERCEL") else "local",
        }

    def score(transactions):
        model = ready()
        raw = [t.model_dump() for t in transactions]
        results = model.predict([{key: r[key] for key in INPUTS} for r in raw])
        for inputs, result in zip(raw, results, strict=True):
            result["prediction_id"] = app.state.store.append(inputs, result)
        return results

    @app.post("/predict")
    def predict(transaction: Transaction):
        return score([transaction])[0]

    @app.post("/predict/batch")
    def batch(payload: Batch):
        return {"predictions": score(payload.transactions)}

    @app.get("/api/samples")
    def samples():
        frame = synthetic(180, seed=73)
        rows = records(frame)
        return {
            "provenance": "Synthetic transactions; not live payments",
            "transactions": [{"transaction_id": f"SYN-{i:06}", **row} for i, row in enumerate(rows[:60])],
        }

    @app.get("/api/model")
    def model_info():
        model = ready()
        evaluation = json.loads((ART / "models" / model.meta["version"] / "evaluation.json").read_text())
        return {"metadata": model.meta, "evaluation": evaluation, "registry": registry()}

    @app.get("/api/drift")
    def drift_info():
        path = ART / "reports/demo-drift.json"
        if not path.exists():
            raise HTTPException(
                503, "Drift demo has not been generated. Run python -m fraudline.monitor --demo."
            )
        return json.loads(path.read_text())

    @app.get("/api/monitoring")
    def monitoring():
        ready()
        path = ART / "reports/monitoring.json"
        return (
            json.loads(path.read_text())
            if path.exists()
            else {"status": "not_run", "samples": 0, "message": "The monitoring job has not run yet."}
        )

    @app.get("/metrics")
    def prometheus():
        report = ART / "reports/monitoring.json"
        if report.exists():
            drift_gauge.set(int(json.loads(report.read_text()).get("drifted", False)))
        return Response(generate_latest(metrics), media_type="text/plain; version=0.0.4")

    static = Path(__file__).parent / "web"
    app.mount("/assets", StaticFiles(directory=static), name="assets")

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/docs", include_in_schema=False)
    def reference():
        return FileResponse(static / "api.html")

    return app


app = create_app()
