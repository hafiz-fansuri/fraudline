# Executed checks — 16 November 2026

## Application and data

- 11 tests passed, including chronological boundaries, batch/single feature parity, schema rejection, join fan-out, model tampering, promotion rejection, drift minimum samples, API contracts, failed-audit error metrics, readiness and rollback.
- Overall coverage 71%; API 90%, data/features 86%, model 97%, audit store 92%. Optional operations integrations have lower unit coverage and were also exercised through the actual stack.
- Ruff and JavaScript syntax checks passed.
- Desktop browser verified at 1440px; mobile at 390px with no horizontal content overflow. Manual $500 test scoring, model evidence, injected drift and scheduled monitoring were inspected.

## Actual local services

The Docker Compose build completed. Fraudline readiness, MLflow health, Grafana health and Prometheus readiness returned HTTP 200 on ports 8013, 5013, 3013 and 9093 respectively. Existing services on port 8000 were left running.

The runtime image measured 878,439,078 bytes before final small source/documentation changes (about 878 MB). Training dependencies are layered separately and cached independently of source edits. MLflow uses one web worker; unrelated MLflow background job execution is disabled because training is operated by this project's pipeline.

## Measured latency

`artifacts/reports/load-test.json`: 60 warm single predictions, concurrency four, p50 40.2 ms, p95 62.3 ms, maximum 76.9 ms, approximately 92.9 requests/second. Includes HTTP, validation, feature transformation, explanation calculation and transactional Postgres audit writes. Cold starts excluded. The first full-stack run missed the target at 209 ms p95; reducing background-worker memory and duplicate scoring work preceded the passing run. Do not extrapolate this short local measurement to hosted free-tier capacity.

## Lifecycle evidence

- Seeded 12,000-row training; logistic regression baseline and LightGBM, calibration and chronological evaluation.
- Six Optuna trials and actual MLflow registry entries/aliases.
- A tuned candidate passed the promotion-window gate; a weaker later candidate was rejected. Final-test hypothetical cost did not beat the logistic baseline, and that result remains visible rather than hidden.
- DVC was executed, not just configured; its content hashes are in dvc.lock. Persistent model outputs preserve the incumbent during a retraining stage.
- `artifacts/reports/lifecycle-demo.json`: 600 synthetic predictions, 200 separately imported synthetic labels, a raised drift flag, and an Evidently HTML report. Retraining waited for a new validated labeled dataset instead of reusing unchanged training data.
- `artifacts/reports/rollback-demo.json`: actual service restart to the previous model, readiness check, restoration of the original champion and another readiness check.
- Actual Postgres privileges checked: the scoring role can INSERT scoring_events and cannot UPDATE or DELETE them. Audit-head mutation is separately permitted for chain linking. This does not provide administrator-proof immutability.

## Security and outstanding external work

The inference dependency audit reported no known vulnerabilities at the time of execution. The optional DVC environment contains an unpatched diskcache advisory; see dependency-notes.md. The full environment is not reported as vulnerability-free.

IEEE-CIS files have not been supplied, so there are no real-dataset metrics. Browser inspection of Render reached its sign-in page: no authenticated Render session was available. Account existence cannot be inferred from that. No public deployment, external alert delivery or GitHub-hosted CI success is claimed. CI and Render configuration are included for those next steps.

The test runner emitted an upstream Starlette/httpx deprecation warning. The runnable project does not depend on replacing the test transport today.
