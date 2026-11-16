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

One Python package owns validation, features and scoring. The hosted image carries a synthetic-only export of the model and UI. Training and monitoring run separately. No cloud secret is needed for local execution.
