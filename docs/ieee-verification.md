# IEEE-CIS execution evidence

Executed 17 November 2026. This report supersedes the earlier synthetic-model verification for the served model.

Model: `fl-20261117072348-496b08`. Data: 590,540 labeled rows, 20,663 fraud labels (3.499%). Prepared-data and raw-file fingerprints are in the exported metadata. No raw/reference rows are exported.

## Chronological partitions

| Interval | Rows | Relative time start | Relative time end |
|---|---:|---:|---:|
| train | 325,908 | 86400 | 8032488 |
| calibration | 88,538 | 8032499 | 10452942 |
| promotion | 88,013 | 10452989 | 13179647 |
| final_test | 88,081 | 13179648 | 15811131 |

## Final held-out comparison

| Metric | Logistic baseline | LightGBM |
|---|---:|---:|
| pr_auc | 0.130068 | 0.461448 |
| roc_auc | 0.799291 | 0.875430 |
| brier | 0.038452 | 0.024289 |
| recall | 0.903426 | 0.781729 |
| false_positive_rate | 0.557036 | 0.193070 |
| cost_per_transaction | 3.236520 | 2.474979 |

Test rows: 88,081. Review threshold 0.033235; block threshold 0.195882. Both models select their own thresholds on calibration data. Costs are hypothetical, not measured savings.

**Material limitation:** 19.3% of legitimate test transactions cross the review threshold. Product W PR-AUC is only 0.0962 despite better aggregate performance. This is not sufficient evidence for real payment authorization. No tuning was performed after seeing final results.

## Executed training

Full dataset, 54 features, 300 LightGBM trees, six seeded Optuna trials inside the training interval. Selected 15 leaves and L2 regularization 3.621062. Sigmoid calibration and cost policy use the calibration interval; promotion and final test are later intervals. No competition test labels exist locally.

Training was executed with source changes in progress. The recorded Git hash is the prior revision, not a clean snapshot of these edits; use the committed implementation and lockfile for reproduction. Training inputs and serialized model hashes are recorded independently.

Commands (PowerShell, repository root):

```powershell
$env:FRAUDLINE_HOME = Join-Path (Get-Location) 'runs/ieee'
.\.venv\Scripts\python.exe -m fraudline.pipeline prepare --ieee ..\ieee-fraud-detection
.\.venv\Scripts\python.exe -m fraudline.pipeline train --tune
.\.venv\Scripts\python.exe -m scripts.test_scenarios
.\.venv\Scripts\python.exe -m scripts.export_demo
```

The initial per-group pandas write path was too slow at full scale; preparation was cancelled and rerun using preallocated NumPy output. The same history parity/leakage tests passed afterward. No dataset sampling was used.

## Synthetic end-to-end results

11/11 expected factor checks passed through FastAPI with the IEEE model. Negative amounts and label injection were rejected. These are serving/control checks, not classifier accuracy.

| Scenario | ML probability | ML decision | Final decision | Activated factors |
|---|---:|---|---|---|
| normal | 0.017483 | approve | approve | None |
| amount | 0.018050 | approve | review | amount |
| card-testing | 0.030309 | approve | review | velocity |
| impossible-travel | 0.018712 | approve | block | location |
| country-mismatch | 0.017483 | approve | review | location |
| new-device | 0.016114 | approve | review | device |
| odd-hour | 0.014689 | approve | review | time |
| merchant | 0.017483 | approve | review | merchant |
| account-takeover | 0.018050 | approve | review | account, amount |
| shared-device | 0.017483 | approve | review | device, network |
| identity | 0.007714 | approve | review | identity |

## Regression verification

30 pytest cases passed; Ruff passed; JavaScript syntax passed. Checks include account isolation, offline/online feature parity, current/equal/future exclusion, all eleven scenario patterns, invalid benchmark types/ranges, model integrity, audit behavior, payload bounds and join fan-out. One installed Starlette/httpx test-client deprecation warning remains; it did not affect results.

## Hosting boundaries

Public Vercel runs inference with an exported, hash-verified IEEE bundle. Raw CSVs, Parquet references, local run folders and secrets are excluded from Git, Docker context and Vercel upload. Public audit storage is ephemeral. Full monitoring/MLflow/Postgres remain optional local operations; they were not re-benchmarked as part of this model experiment.

The local browser scenario workflow passed 11/11 checks with the IEEE model. Desktop (1440px) and mobile (390px) layouts were inspected. Mobile testing found grid overflow; shrinkable grid columns fixed it. The final 390px check showed no page-wide horizontal overflow. Navigation, model evidence and the full learning guide were inspected; Operations retains monitoring/metrics access. See `ieee-workbench.jpg` for the verified interface.

## Public release verification

Published to [fraudline.vercel.app](https://fraudline.vercel.app), Vercel deployment `dpl_EeVJc5c12ayvDcvXAsMynbsttSZD`, serving model `fl-20261117072348-496b08`. Public `/ready` returned 200, source `ieee-cis`, and ephemeral audit storage. `/api/model` confirmed 54 features. The guide, downloadable Markdown, API reference, JavaScript and stylesheet returned 200.

All eleven authored synthetic scenarios were also scored through the public production batch endpoint: 11/11 expected-factor checks passed. The baseline approved; impossible travel blocked; the remaining stress cases requested review through explicit controls. An invalid negative amount returned 422. These are synthetic policy/serving checks, not a fraud-accuracy benchmark.

[GitHub verification for the implementation](https://github.com/hafiz-fansuri/fraudline/actions/runs/44042139861) completed successfully: regression tests, committed IEEE bundle/scenario checks, synthetic lifecycle smoke run, inference dependency audit and Docker build. Heavy training remains local; the original full Docker operations stack was not restarted or re-benchmarked for this release.

## Learning materials

[Full A–Z guide](learning-guide.md) · [Training source](../fraudline/pipeline.py) · [Model card](model-card.md)
