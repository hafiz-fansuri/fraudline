# Model card

Intended use: educational demonstration of a reproducible fraud-scoring lifecycle. Not approved for real authorization, adverse financial decisions or customer profiling.

Data: seeded synthetic amounts, products, card metadata, identity availability, distances and binary targets. IEEE-CIS importer exists but real competition data has not been supplied. The synthetic label generator is known, simplified and not representative of real fraud.

Model: LightGBM on log amount/distance, missingness, categorical indices and cyclic time-offset features. Time offset is a relative clock; it is not a verified wall-clock hour. A logistic regression provides a baseline. Sigmoid calibration uses a separate chronological interval. Review/block thresholds minimize a hypothetical loss matrix; calibration and threshold selection share that interval and need further validation before any operational use.

Evaluation: earlier 55% training, next 15% calibration/threshold selection, next 15% promotion, final 15% assessment, split on distinct timestamps. Inspect `artifacts/reports/latest-training.json` for executed metrics, product slices and row counts. PR-AUC, ROC-AUC, Brier, recall, false-positive rate and hypothetical cost are reported. No metric is hardcoded into the application.

Promotion: require an improvement in PR-AUC over the incumbent, no higher hypothetical cost, and no recall regression larger than three percentage points. Initial training bootstraps the registry; it is not a claim that every metric beats the baseline. Product-slice reporting is diagnostic, not a fairness certification.

Explanations: LightGBM `pred_contrib=True`; contributions are raw-score/log-odds associations before calibration, not percentage-point effects or causal reasons. Card network/product categories are proxies; do not infer protected attributes or claim fairness from these slices.

Limitations: no history-window features, label delay modeling, capacity-aware review optimization or validated production cost estimates. Performance on synthetic data cannot be extrapolated to real payments. Reusing reported final test results to tune models invalidates their holdout status.
