import json
import math
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
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from fraudline.data import ANON_NUMERIC, INPUTS, MATCH_FIELDS, synthetic
from fraudline.history import enrich
from fraudline.model import Model
from fraudline.pipeline import ART, ROOT, registry
from fraudline.signals import FACTOR_COVERAGE, combine, controls
from fraudline.store import Store


class HistoryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    amount: float = Field(gt=0, le=1_000_000, strict=True)
    time_offset: int = Field(ge=0, le=10_000_000_000, strict=True)
    account_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    device_type: Literal["desktop", "mobile", "unknown"] = "unknown"
    payer_email_domain: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9.-]+$")
    device_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    ip_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    billing_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    device_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    merchant_category: Literal["general", "gift_cards", "crypto", "gambling"] = "general"
    failed_logins_1h: int = Field(default=0, ge=0, le=1000, strict=True)
    password_changed_minutes: int | None = Field(default=None, ge=0, le=1_000_000, strict=True)
    new_payee: StrictBool = False
    withdrawal: StrictBool = False
    identity_match: StrictBool | None = None
    disposable_email: StrictBool = False


class Transaction(HistoryEvent):
    transaction_id: str = Field(default="manual", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    product: Literal["W", "C", "R", "H", "S"]
    network: Literal["visa", "mastercard", "american express", "discover", "unknown"]
    card_type: Literal["debit", "credit", "unknown"]
    distance: float | None = Field(default=None, ge=0, le=100_000, strict=True)
    identity_present: StrictBool
    receiver_email_domain: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9.-]+$")
    address_region: float | None = Field(default=None, ge=0, le=1_000_000)
    issuer_region: float | None = Field(default=None, ge=0, le=1_000_000)
    history: list[HistoryEvent] = Field(default_factory=list, max_length=200)
    context: Context = Field(default_factory=Context)
    benchmark_signals: dict[str, float | Literal["T", "F"] | None] = Field(
        default_factory=dict, max_length=28
    )

    @model_validator(mode="after")
    def known_benchmark_fields(self):
        if not set(self.benchmark_signals).issubset([*ANON_NUMERIC, *MATCH_FIELDS]):
            raise ValueError("Unknown anonymized IEEE benchmark field")
        for name, value in self.benchmark_signals.items():
            if value is None:
                continue
            if name in ANON_NUMERIC and (
                not isinstance(value, (int, float)) or not math.isfinite(value) or not -1 <= value <= 1e9
            ):
                raise ValueError("IEEE count/duration fields must be finite numbers between -1 and 1e9")
            if name in MATCH_FIELDS and value not in ["T", "F", 0, 1]:
                raise ValueError("IEEE match fields must be T, F, 0, 1 or null")
        return self


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transactions: list[Transaction] = Field(min_length=1, max_length=100)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: Transaction
    question: str = Field(
        default="What evidence and human review steps apply to this transaction?",
        min_length=2,
        max_length=1200,
    )


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
                if size > 262144:
                    return JSONResponse({"detail": "Request body exceeds 256 KiB"}, 413)
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
            "default-src 'self'; connect-src 'self' https://fszqzfxiegkxubiasllh.supabase.co; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
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
        enriched = [
            enrich(
                {
                    key: value
                    for key, value in r.items()
                    if key not in ["history", "context", "benchmark_signals"]
                }
                | r["benchmark_signals"],
                r["history"],
            )
            for r in raw
        ]
        results = model.predict(enriched)
        for inputs, values, result in zip(raw, enriched, results, strict=True):
            result["model_decision"] = result["decision"]
            result["signals"] = controls(values, inputs["history"], inputs["context"])
            result["decision"] = combine(result["model_decision"], result["signals"])
            result["history_features"] = {
                key: values[key]
                for key in [
                    "transactions_1h",
                    "transactions_24h",
                    "transactions_7d",
                    "small_charges_10m",
                    "amount_ratio_7d",
                    "amount_zscore_7d",
                    "unusual_hour",
                    "device_type_new",
                ]
            }
            result["factor_coverage"] = FACTOR_COVERAGE
            result["prediction_id"] = app.state.store.append({key: values.get(key) for key in INPUTS}, result)
        return results

    @app.post("/predict")
    def predict(transaction: Transaction):
        return score([transaction])[0]

    @app.post("/predict/batch")
    def batch(payload: Batch):
        return {"predictions": score(payload.transactions)}

    @app.post("/api/review")
    def review(payload: Review):
        from fraudline.investigation import investigate

        result = score([payload.transaction])[0]
        return {
            "transaction_id": payload.transaction.transaction_id,
            "risk": result,
            "investigation": investigate(result, payload.question),
        }

    @app.get("/api/playbooks")
    def playbooks():
        from fraudline.investigation import sources

        return {"sources": sources(), "external_calls": False}

    @app.get("/api/samples")
    def samples():
        frame = synthetic(180, seed=73)
        rows = (
            frame[
                [
                    "amount",
                    "time_offset",
                    "product",
                    "network",
                    "card_type",
                    "distance",
                    "identity_present",
                    "account_id",
                    "device_type",
                    "payer_email_domain",
                    "receiver_email_domain",
                ]
            ]
            .replace({float("nan"): None})
            .to_dict("records")
        )
        return {
            "provenance": "Synthetic transactions; not live payments",
            "transactions": [{"transaction_id": f"SYN-{i:06}", **row} for i, row in enumerate(rows[:60])],
        }

    @app.get("/api/factors")
    def factors():
        return {
            "factors": FACTOR_COVERAGE,
            "probability_note": "Contextual controls can escalate the decision without altering the calibrated model probability.",
        }

    @app.get("/api/scenarios")
    def scenario_list():
        from fraudline.scenarios import scenarios

        return {
            "provenance": "Synthetic operational scenarios; not a real-world accuracy estimate",
            "scenarios": scenarios(),
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
        return FileResponse(static / "desk.html")

    @app.get("/checker", include_in_schema=False)
    def checker():
        return FileResponse(static / "client.html")

    @app.get("/workbench", include_in_schema=False)
    def workbench():
        return FileResponse(static / "index.html")

    @app.get("/docs", include_in_schema=False)
    def reference():
        return FileResponse(static / "api.html")

    @app.get("/guide", include_in_schema=False)
    def learning_guide():
        return FileResponse(static / "guide.html")

    return app


app = create_app()
