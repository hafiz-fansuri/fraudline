# Fraudline

A fraud detection MLOps project with a transaction investigation desk: real trained-model predictions, calibrated scores, reason contributions, model lineage and an injected drift demonstration.

**Current data is synthetic.** IEEE-CIS data has not been supplied. Synthetic metrics demonstrate the pipeline; they do not establish real fraud detection quality. This is a portfolio demonstration, not a banking service.

## Run without Docker

Install Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/). From this directory:

```sh
uv sync --frozen --extra dev --extra ops
uv run python -m fraudline.pipeline demo
uv run python -m fraudline.monitor --demo
uv run uvicorn fraudline.api:app --host 127.0.0.1 --port 8012
```

Open http://127.0.0.1:8012. On this Windows checkout, the installed environment is `.venv\Scripts\python.exe`; use it in place of `uv run python`. No account, API key or payment card is needed for the local demonstration.

## Start the complete local stack

Start Docker Desktop or another Docker daemon first. Then:

```sh
make up
# Windows without make:
python scripts/up.py
```

This generates ignored local passwords and starts Postgres, MLflow, bootstrap training, the API, a five-minute monitor, Prometheus and Grafana. Services bind to loopback. Open the desk on port 8013, MLflow on 5013, Prometheus on 9093 and Grafana on 3013. Grafana username is `admin`; its generated password is in `.env`. Do not expose this development stack directly to the Internet.

## What works

- Joined-data import with one-to-one validation, schema gates, dataset hashes and chronological splits without timestamp overlap.
- Logistic baseline, bounded optional Optuna search, LightGBM, sigmoid calibration, cost-tuned review/block thresholds and product-slice reports.
- Champion/challenger gate and one-command rollback. Model bundles include source/data lineage, feature schema, thresholds and a verified model hash.
- FastAPI single/batch predictions, bounded payloads, strict request contract, process-local rate limit, model version and native LightGBM contributions.
- Transactional hash-linked audit records using SQLite locally or Postgres in Compose. The Compose scoring role cannot update/delete scoring events. This is tamper evidence, not administrator-proof immutable storage.
- Delayed-label import and performance metrics; scheduled drift reports with Evidently HTML, local alerts, optional webhook delivery, and retraining only when newly prepared labeled data is available.
- DVC cached stages, MLflow tracking/registry when configured, Prometheus/Grafana, CI definition, Render deployment blueprint and test suite.
- Responsive investigation UI with seeded replay, manual test scoring, reason contributions, evaluation artifacts, model history, monitoring and computed synthetic drift scenarios.

## Reproduce with DVC

```sh
git init  # only if this directory is not already its own repository
uv run dvc init
uv run dvc repro
```

`dvc.lock` records content hashes after execution. Raw data and local model artifacts stay outside ordinary Git. A local DVC cache is sufficient to replay on this computer; configure an authorized remote before sharing reproducibility across computers. Do not upload competition data into a public remote.

## Train on IEEE-CIS

Download the competition files yourself after accepting the [Kaggle terms](https://www.kaggle.com/competitions/ieee-fraud-detection/rules). Use a separate working directory via `FRAUDLINE_HOME` for IEEE artifacts so synthetic and IEEE model registries are never mixed:

```sh
FRAUDLINE_HOME=/absolute/path/ieee-run uv run python -m fraudline.pipeline prepare --ieee /path/to/csvs
FRAUDLINE_HOME=/absolute/path/ieee-run uv run python -m fraudline.pipeline train --tune
```

PowerShell: set `$env:FRAUDLINE_HOME = 'C:\path\ieee-run'` before the commands. Required files are `train_transaction.csv` and `train_identity.csv`. The first import deliberately uses a compact, stateless subset of shared features. It must not imply all anonymized IEEE fields are available at real authorization time.

## Operations

```sh
uv run pytest --cov=fraudline --cov-report=term-missing
uv run python -m fraudline.benchmark --url http://127.0.0.1:8013
uv run python -m fraudline.monitor
uv run python -m fraudline.pipeline train --tune
uv run python -m fraudline.pipeline rollback
uv run python -m scripts.labels delayed-labels.csv
```

Restart the API after promotion/rollback; it pins a verified bundle at startup. `make rollback` restarts the Compose API automatically. Set `MLFLOW_TRACKING_URI` to log runs and register aliases. Without it, the local JSON bundle registry is authoritative. Do not run multiple independent lifecycle operators against the same workspace.

See [runbook](docs/runbook.md), [model card](docs/model-card.md) and [architecture](docs/architecture.md).

## Free hosted demo

`uv run python -m scripts.export_demo` exports only the synthetic champion into `demo-bundle`. The runtime Docker image loads this same model; it never trains at request time. Deploy the repository using `render.yaml`, then disable Render's direct auto-deploy and add a Render deploy hook as GitHub's `RENDER_DEPLOY_HOOK` secret to deploy only after CI passes. Keep hook URLs secret.

Render Free sleeps when idle and its disk is ephemeral. Hosted audit records can disappear on restart; do not claim persistent compliance logging there. Free quota availability is outside this repository's control. CI configuration is not a green CI run or a deployment until it has actually executed on GitHub.

## Explicit limits

No enterprise feature store, Kubernetes, Kafka or LLM. Past-window card/device history features are deferred until the serving path has durable event-time state and tested ordering semantics. No production payment processing, causal explanations or demonstrated financial savings. An untouched final interval is reported for assessment, never used by the promotion gate; stop using it as a final holdout if you iterate against its published results.
