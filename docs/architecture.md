# Architecture

```mermaid
flowchart LR
  Data[Authorized IEEE CSVs or seeded synthetic tables] --> Validate[Pandera validation and hash lineage]
  Validate --> Parquet[Parquet / DVC cache]
  Parquet --> Train[Chronological train and calibration]
  Train --> Gate[Promotion-window champion gate]
  Gate --> Bundle[Versioned LightGBM bundle]
  Train --> MLflow[MLflow tracking and registry aliases]
  Bundle --> API[FastAPI / shared features]
  API --> Desk[Transaction investigation desk]
  API --> Log[Transactional audit chain]
  Log --> Monitor[Evidently and drift monitor]
  Labels[Delayed labels] --> Monitor
  Monitor --> Candidate[New labeled-data retraining candidate]
  Candidate --> Gate
  API --> Prometheus[Prometheus metrics]
  Prometheus --> Grafana[Grafana and alert rules]
```

One Python package owns validation, features and scoring. The hosted bundle carries the IEEE-trained model, aggregate evidence, authored synthetic scenarios and UI; source/reference rows are excluded. Past-only history is shared by preparation and request enrichment. Context controls may escalate the decision without changing calibrated probability. Training and monitoring run separately. See the [A–Z guide](learning-guide.md) for coverage and trust boundaries.
