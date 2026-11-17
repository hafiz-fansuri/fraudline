# Model card

Intended use: educational demonstration of a reproducible fraud-scoring lifecycle. Not approved for real authorization, adverse financial decisions or customer profiling.

Data: the supplied IEEE-CIS labeled training files, joined one-to-one on TransactionID: 590,540 transactions, 20,663 fraud labels (3.499%). Unlabeled competition test files are not used for accuracy claims. Raw data and training/reference rows are excluded from public export. Authored synthetic scenarios test serving and policies, not real-world classifier accuracy.

Model: LightGBM on 54 inputs, including log amount/distance, missingness, categorical indices, cyclic relative time, past-only amount/velocity/device/domain history, anonymized C/D/M fields and region proxies. Entity history uses hashed card/address composites, not verified accounts. Time offset is relative, not verified local time. Logistic regression supplies a baseline. Sigmoid calibration and cost-threshold selection share a calibration interval; each model selects its own thresholds. Exact feature order, parameters and metrics are in the exported bundle.

Evaluation: earlier 55% training, next 15% calibration/threshold selection, next 15% promotion, final 15% assessment, split on distinct timestamps. Inspect `artifacts/reports/latest-training.json` for executed metrics, product slices and row counts. PR-AUC, ROC-AUC, Brier, recall, false-positive rate and hypothetical cost are reported. No metric is hardcoded into the application.

Promotion: require an improvement in PR-AUC over the incumbent, no higher hypothetical cost, and no recall regression larger than three percentage points. Initial training bootstraps the registry; it is not a claim that every metric beats the baseline. Product-slice reporting is diagnostic, not a fairness certification.

Explanations: LightGBM `pred_contrib=True`; contributions are raw-score/log-odds associations before calibration, not percentage-point effects or causal reasons. Card network/product categories are proxies; do not infer protected attributes or claim fairness from these slices.

Context: nine factors are covered by trained features, explicit controls, or both. GPS travel, IP/billing mismatch, physical device links, merchant categories, password/payee events, disposable-email and verified identity flags are supplied contextual controls absent from IEEE. They can escalate final decisions without altering the calibrated ML probability. No external identity/geolocation service or trained fraud-ring graph is connected.

Limitations: anonymized benchmark aggregates have uncertain authorization-time semantics. The public API trusts supplied history (maximum 200 events); production needs a trusted, complete history source. Relative time and grouping proxies can be misleading. No capacity-aware review optimization, independently validated costs or external-bank validation. Public Vercel audit storage is ephemeral. Reusing final test metrics for tuning invalidates holdout status. See the [A–Z guide](learning-guide.md) and [executed IEEE report](ieee-verification.md).
