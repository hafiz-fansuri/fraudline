# Runbook

## No model loaded
`/health` is liveness; `/ready` returns 503 until a verified model is available. Run the demo pipeline and drift demo, then restart the API. A corrupted model hash or incompatible feature schema must fail closed; never bypass the verification to make readiness green.

## Train and promote
Prepare a validated dataset, then run `python -m fraudline.pipeline train`. Optional `--tune` runs six bounded Optuna trials. JSON evidence lives beside each immutable model bundle. Equal candidate metrics do not replace a champion. Use an explicit artifact promotion/deployment boundary: updating the registry does not hot-swap an active service.

## Roll back
Run `python -m fraudline.pipeline rollback`, verify the registry history, then restart the API and check `/ready` model version. `make rollback` includes the Compose restart. Rollback needs an actual previous promoted champion; it cannot fabricate one after the first training run.

## Monitoring and labels
Run `python -m fraudline.monitor` or use the Compose monitor (every five minutes). At least 100 current-model samples are required for data drift. Import delayed labels from a CSV with `prediction_id,is_fraud` using `python -m scripts.labels file.csv`. At least 30 labeled rows and both classes are needed for aggregate performance metrics. Monitor is separate from the public API; no retrain/promotion endpoints exist.

`python -m fraudline.monitor --retrain` only attempts a new candidate when drift exceeds the threshold, a new labeled dataset has been prepared, and 24 hours have elapsed since a successful retraining attempt. The lifecycle lock prevents concurrent training/rollback; after a crash, confirm no process is running before removing a stale lock directory. Never turn prediction scores into training labels.

`ALERT_WEBHOOK_URL` optionally sends a drift notification to a webhook you own. Without it the report records a local alert. Prometheus separately evaluates error-rate and latency alert rules; external alert routing requires an Alertmanager setup and is not silently enabled.

## Audit records
SQLite serializes local writes; Postgres uses a locked audit-head row. Compose grants the scoring role only insert/select on scoring events and select/update on the audit head. Verify a chain by recomputing SHA-256 over previous digest, UUID, timestamp and exact payload. Hash links do not prevent a database administrator from rewriting the chain. Back up Postgres volumes and store externally signed checkpoints before claiming stronger integrity.

## Hosted service
The Render free plan can cold-start and lose its local disk. Store only synthetic/manual illustrative inputs. Do not send actual card numbers, email addresses or personal data. Public demo throttling is single-process and bounded; use an authenticated gateway/shared limiter before multi-worker or production operation.

## Secrets and shutdown
Local passwords live in ignored `.env`. Do not paste it into issues. `docker compose down` preserves named data volumes; never use `down -v` unless you intend to remove all local databases. An existing Postgres volume retains its original password; changing `.env` alone does not rotate the database credentials.
