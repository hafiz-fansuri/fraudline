# Fraudline: the complete A–Z learning guide

A practical walkthrough: what was built, how it works, why these choices were made, how to reproduce it, and what its results actually mean.

## Results of this executed experiment

The experiment for model `fl-20261117072348-496b08` used all 590,540 supplied labeled transactions across chronological partitions, with 54 features. The trees fitted 325,908 earlier transactions; 88,538 calibrated probabilities/thresholds, 88,013 assessed promotion, and 88,081 formed the final later holdout. Holdout labels never fitted the trees. LightGBM average precision is 0.4614 versus logistic regression 0.1301; ROC-AUC is 0.8754; Brier score is 0.02429. At the selected review threshold, fraud recall is 78.17% and legitimate false-positive rate is 19.31%. That review burden is substantial. Product W average precision is only 0.0962, an important weakness hidden by the aggregate metric.

All 11 authored synthetic cases passed their expected-factor checks through the actual IEEE-model API. Thirty regression tests passed. These checks establish serving/control behavior, not real-world accuracy. Review threshold is 0.033235 and block threshold 0.195882, chosen using the illustrative calibration-period costs described below. The separate execution report includes exact split counts, baseline comparison and scenario-by-scenario results.

## A. What this project does

Fraudline is an educational fraud investigation application. A Python API scores a transaction with a trained machine-learning model, explains its strongest model contributions, applies contextual risk controls, and saves a decision record. The browser lets you investigate authored synthetic cases and inspect actual training evidence.

It does not move money, connect to a payment processor, identify real people, or prove that somebody committed fraud. The public deployment should receive synthetic inputs only.

The key distinction is **probability versus decision**. LightGBM estimates fraud probability using features learned on IEEE-CIS. Explicit controls can escalate an approve to review or block. They never silently change that calibrated probability. The receipt shows both the model decision and the final decision.

## B. Architecture: follow one transaction

```text
IEEE transaction CSV + identity CSV
  → validate and one-to-one join
  → pseudonymous entity proxy + past-only history features
  → chronological train / calibration / promotion / final test
  → logistic baseline + LightGBM + sigmoid calibration
  → verified model bundle: weights, metadata, evaluation

Synthetic case + supplied history + optional context
  → Pydantic API validation
  → shared feature builder
  → calibrated probability + TreeSHAP explanation
  → contextual controls + most restrictive decision
  → hash-linked audit record
  → investigation receipt in the browser
```

The optional local operations stack adds PostgreSQL, MLflow, Prometheus, Grafana, and a monitoring worker. The public Vercel deployment runs interface and inference without that whole stack. Its temporary filesystem is not durable storage.

## C. Understanding the IEEE-CIS files

Your `train_transaction.csv` contains 590,540 labeled transactions, including 20,663 fraud labels: approximately 3.50%. `train_identity.csv` provides optional identity/device fields. `TransactionID` joins them. The importer validates a one-to-one join, so duplicated identity IDs cause an error instead of silently multiplying rows. Transactions without identity information remain valid.

The competition test files do not contain fraud labels. We cannot calculate honest test accuracy from them. Instead, we reserve a later interval from the labeled training transactions.

The importer reads selected columns instead of all hundreds of V fields. This reduces memory, training time, feature complexity, and serving size. It is a practical portfolio baseline, not a Kaggle leaderboard solution.

`TransactionDT` is seconds from a reference point, not a verified calendar timestamp or customer timezone. `ProductCD` is an anonymized product code, not a merchant category code. `dist1` is an anonymized distance field, not GPS distance in a known unit. C, D, and M fields are anonymized aggregates/matches; their exact production availability is not established here.

The entity proxy is a deterministic BLAKE2 hash of anonymized card/address fields. It groups repeat behavior but is not a verified customer account. Two people can share the same grouping values. Hashing is pseudonymization, not a guarantee of anonymity or correct identity.

Raw CSVs, prepared rows, reference rows, databases, and credentials are excluded from Git and public deployment. Only trained weights, aggregate metrics, metadata, and authored synthetic examples are exported. Keep the original data under its competition access/use terms; do not redistribute it as portfolio sample records.

## D. The code map — including the actual training file

| File | Responsibility |
|---|---|
| `fraudline/data.py` | IEEE import, validation, shared features, chronological split |
| `fraudline/history.py` | Past-only account history calculations, shared offline/online |
| `fraudline/pipeline.py` | **Actual training**, tuning, calibration, thresholds, evaluation, registry |
| `fraudline/model.py` | Verified LightGBM inference and TreeSHAP explanations |
| `fraudline/signals.py` | Nine-factor coverage and explicit contextual controls |
| `fraudline/scenarios.py` | Eleven authored synthetic operational scenarios |
| `fraudline/api.py` | HTTP validation and scoring orchestration |
| `fraudline/store.py` | Transactional audit records and delayed labels |
| `fraudline/monitor.py` | Drift, labeled performance, guarded retraining |
| `fraudline/web/` | HTML, CSS, JavaScript, and the learning guide |
| `scripts/export_demo.py` | Public-safe model export, excluding training records |
| `scripts/test_scenarios.py` | Synthetic end-to-end API checks and saved report |
| `tests/` | Regression checks, history parity/leakage checks, API checks |
| `app.py` | Vercel entrypoint and native runtime adaptation |

**Open `fraudline/pipeline.py`, function `_train()`. The `LGBMClassifier(...).fit(x, y)` call is where the model learns.** The public `train()` wrapper adds a lifecycle lock. Clicking Analyze in the browser performs inference with a previously trained model; it does not retrain it.

## E. Why these technologies

Python fits this tabular workflow. pandas handles tables, NumPy handles numerical windows, Pandera validates training data, and Pydantic validates untrusted API requests. These validation layers serve different boundaries: training-data consistency versus HTTP payload safety.

LightGBM learns nonlinear relationships and interactions efficiently on structured data. Its native tree format is compact, and it supports contribution explanations without an additional SHAP package. A deep network would add complexity and serving weight without evidence this project needs it.

Logistic regression supplies a simpler reference model. StandardScaler prevents wide-range numeric features from dominating its numerical optimization. Both models use the same inputs and later test rows. The comparison helps establish whether the more complex model adds value.

FastAPI provides typed HTTP validation and ASGI serving. Plain HTML, CSS, and JavaScript are enough for this interface; adding a frontend framework would introduce another build system and dependency tree without solving a current requirement.

SQLite supports simple local/ephemeral operation; PostgreSQL supports the durable local stack. SQLAlchemy supports both. MLflow records experiments and model aliases, Docker Compose runs the optional services, and Prometheus/Grafana expose operational health. None is required just to run one prediction on Vercel.

## F. How raw inputs become model features

A feature is a numeric input the model can use. `data.py:features()` is shared by training and inference. Reimplementing it in browser JavaScript would risk different encodings at serving time.

The contract includes log amount, cyclic relative time, product/network/card-type codes, log distance and distance missingness, identity availability, eleven history features, device type, payer/receiver domain buckets and mismatch, anonymized region codes, C1–C14, selected D fields, and M match flags.

A feature being available during fitting does not guarantee the trees use it. Zero gain means no selected split used that input in this model; for example, the small-charge feature has zero gain in this run. Its separately authored card-testing policy still activates in the synthetic scenario. Do not confuse input coverage with demonstrated learned detection quality.

`log1p(amount)` compresses a long monetary tail while preserving order. Missing distance has its own indicator, so missing is distinguishable from a confirmed zero. Unavailable anonymized numbers use -1. Match flags encode true as 1, false as 0, and unknown as -1.

Sine and cosine encode time cyclically, placing the end of a relative day close to its beginning. They do not establish an actual local hour. Domain buckets use a stable hash; Python's ordinary `hash()` is process-randomized and unsuitable for persisted encodings. Hash buckets can collide. The API accepts domains rather than full email addresses.

Categorical integer codes are a compact baseline. Trees can split them numerically, so artificial ordering is a modeling limitation. Native categorical treatment, richer V features, and stronger entity definitions are possible research comparisons on a new validation interval.

Some anonymized benchmark aggregates may not be available at real authorization time. Their precise timing semantics are unknown here. Missing C/D/M values in manual examples can shift the score relative to the training population. This is why the application is a benchmark workbench rather than a production authorization claim.

## G. History features without future leakage

For each entity proxy, we calculate counts over one hour, one day, and seven days; charges of $5 or less in ten minutes; amount divided by its preceding seven-day average; amount z-score; seconds since the previous event; unseen relative hour; new device type; and payer-domain change.

For time t, the seven-day window includes events at or after t−604800 and **strictly before t**. The current event, equal-time peers, and future events are excluded. Equal-time events cannot be reliably ordered, so neither may borrow information from the other.

Sorted groups, cumulative sums, and binary searches make windows efficient. A window sum is a subtraction of two cumulative totals. Squared-amount totals provide variance. Missing-history defaults are counts 0, amount ratio 1, z-score 0, and previous-event delay -1. The history-available flag indicates an identifiable grouping key; inspect the count fields to establish whether prior events actually exist.

Example: prior amounts 10 and 20 average 15. A new amount 90 gives a 6× ratio. That is unusual, not proof of fraud. With fewer than two prior amounts the z-score defaults to zero because its variance estimate is unstable.

History is computed before the global time split but uses only earlier **unlabeled** events. That lets a later evaluation transaction use genuinely earlier activity, as an online system could. Fraud labels never enter history calculations.

The public API accepts at most 200 supplied historical events. A caller can omit or falsify them. Production must retrieve complete, trusted history through an authenticated backend. Offline full history and truncated request history can differ. The request-local design makes this demo reproducible and inexpensive, but is not a trusted feature store.

## H. The chronological experiment

Distinct timestamps define approximately 55% training, 15% calibration/thresholds, 15% promotion, and 15% final test. Exact row counts differ because event density varies over time. Equal timestamps never cross split boundaries.

Random splitting can place nearly repeated or simultaneous activity on both sides. Chronological testing better approximates future scoring. It still uses one benchmark population; it is not external validation on a different bank.

Optional Optuna tuning runs six seeded trials on an internal chronological split inside the training interval. It varies leaf count and L2 regularization using average precision. Calibration, promotion, and final labels do not select those hyperparameters.

The chosen LightGBM configuration then fits all training rows. IEEE uses 300 trees, two worker threads, seeded deterministic options, and explicit binning/regularization. Metadata records effective parameters. Hardware/library changes can still affect reproduction; the lockfile and serialized model preserve the executed environment and weights.

Do not repeatedly adjust the model after viewing final metrics while still calling that interval untouched. A new iteration needs a fresh holdout or a properly designed temporal backtest.

## I. Calibration: from raw score to probability

The tree model emits a raw score. A separate logistic regression learns a sigmoid mapping on the calibration interval:

```text
p = sigmoid(slope × raw_score + intercept)
sigmoid(z) = 1 / (1 + exp(-z))
```

This improves the mapping from ranking score to observed fraud probability. It does not guarantee reliability after the population changes. Brier score measures mean squared probability error; a lower value is better on the same population.

Calibration and threshold selection share one interval, which is practical but optimistic for selection on that interval. The final later interval provides a separate assessment. Production would also need reliability diagrams, uncertainty assessment, and ongoing calibration checks.

## J. Approve, review, or block

Two thresholds are chosen from a calibration grid. Below review means approve; at/above block means block; the middle means manual review. The illustrative loss assumes a fraudulent approval loses the amount, a review costs $3 and misses 20% of fraudulent value, and a false block costs $15.

These are example assumptions, not measured business costs. Each model chooses its own thresholds before final evaluation, so the logistic baseline is not unfairly assessed using LightGBM's selected policy.

Changing costs changes recall, false-positive rate, and review volume. Real deployment must consider investigator capacity, customer harm, appeals, and chargeback economics. The displayed cost is not a claim of actual financial savings.

## K. Read the metrics correctly

| Metric | Meaning | Caution |
|---|---|---|
| PR-AUC / average precision | How strongly the ranking concentrates fraud among alerts | Depends on prevalence; not ordinary accuracy |
| ROC-AUC | Ranking of fraudulent versus legitimate events | Can look strong with severe imbalance |
| Recall | Fraction of fraud at/above the review threshold | High recall may require many legitimate reviews |
| False-positive rate | Fraction of legitimate events at/above review | Not fraud precision |
| Brier score | Mean squared probability error | Compare on the same population |
| Cost / transaction | Average hypothetical loss | Not actual bank losses |

An always-approve model could look approximately 96.5% accurate here while catching zero fraud. This is why ordinary accuracy is not the headline.

The Model evidence page reads actual `evaluation.json`, comparing the two models on the same later rows. Product slices diagnose uneven behavior; they are not fairness certification. Anonymized categories do not establish protected-group fairness.

Promotion requires promotion-set PR-AUC improvement greater than 0.001, no increased hypothetical cost, and no recall loss beyond three percentage points against the incumbent. The first model bootstraps an empty registry; this does not certify production quality. IEEE and synthetic champions are kept in separate runs because their metrics describe different populations.

## L. The nine requested factors

| Factor | Trained IEEE inputs | Explicit contextual controls |
|---|---|---|
| Amount | Amount, ratio, z-score, small-charge count | ≥5× average with ≥3 prior events; ≥4 small charges / 10 min |
| Velocity | 1-hour, 1-day, 7-day counts | ≥8 transactions / hour; ≥5 login failures |
| Location | Anonymized distance/region proxies | IP/billing-country mismatch; travel >500 km and >900 km/h |
| Device | Desktop/mobile type and novelty | New physical device ID; shared-device links |
| Time | Relative cyclic hour and unseen history hour | Unseen hour after ≥5 prior events |
| Merchant | Product proxy, not merchant category | Gift cards, crypto, gambling request review |
| Account | No password/payee data in IEEE | Password change ≤30 min with amount ≥500; new payee + withdrawal |
| Network | No trained fraud graph | Device shared by ≥4 distinct accounts in prior 24 hours |
| Identity | Domain comparison, identity availability, M flags | Supplied identity mismatch/disposable-email flags |

Travel uses Haversine great-circle distance divided by elapsed hours. It is a simple policy with false positives from shared accounts or inaccurate locations. It does not query IP geolocation or know actual travel.

The network check counts one-hop shared-device relationships. It is not a graph neural network or validated fraud-ring detector. Phone/address network links are not inferred because trustworthy inputs were not supplied.

Even when a history feature is trained, the hard-coded rule using that feature remains separate policy. The combined decision takes the most restrictive outcome. A model block cannot be downgraded by benign context. Unsupported context is never presented as learned from IEEE.

## M. Explaining a prediction

`model.py` calls LightGBM with `pred_contrib=True`. TreeSHAP returns contributions plus a bias. Their sum equals the raw tree score; calibration then maps it to probability.

The interface shows the three largest absolute contributions. Positive raises raw risk relative to model bias; negative lowers it. Values are uncalibrated log-odds, not percentage points. The top three alone do not sum to the whole score. Correlated features can share importance. These are associations, not causal proof.

Feature gain in Model evidence is accumulated training split improvement. It differs from an individual TreeSHAP explanation. Neither measure justifies treating a person as a criminal.

## N. Synthetic testing: what it proves

Eleven authored scenarios cover baseline, amount spike, card testing, impossible travel, country mismatch, new device, unusual hour, risky merchant, account takeover pattern, shared device, and identity mismatch. None copies an actual IEEE row.

Each contains a current event, illustrative history, and optional context. The baseline expects no contextual findings. Each stress case expects its relevant factor. Scenario names describe intended tests, not ground-truth labels for classifier accuracy.

The browser suite sends all eleven through the actual batch API. The Python report additionally checks finite bounded probabilities, model provenance, decision escalation, prediction IDs, and rejection of invalid payloads. These checks test serving and controls. Real-world classifier performance is evaluated separately on held-out labeled IEEE data.

Editing amount/device changes a request and may invalidate its original expected pattern. The suite uses original authored cases to remain reproducible. A baseline may still get an ML review: no contextual finding is different from guaranteed model approval.

## O. API: request, validate, score, explain

Get full examples with `GET /api/scenarios`, then send a scenario's `transaction` to `POST /predict`. Batch requests use `{ "transactions": [...] }`, with at most 100 events.

Amount, relative time, product, network, card type, and identity availability form the base request. Optional account/domain/device fields, history, context, and whitelisted C/D/M benchmark signals extend it. Labels and arbitrary model-feature injection are not accepted.

Responses contain probability, initial model decision, final decision, thresholds, model version, reasons, contextual findings, computed history, factor coverage, and an audit ID. Invalid bounds, unknown keys, non-finite numbers, oversized history, or invalid enums are rejected. Bodies above 256 KiB and excessive per-process rates are limited.

`/ready` checks a verified model loaded; `/health` only checks the process is alive. `/api/model` exposes model evidence, `/api/factors` coverage, `/metrics` Prometheus metrics, `/docs` API reference, and `/guide` this manual.

The limiter is a demo per-process control, not distributed abuse protection. There is no authenticated browser training endpoint. Operational use needs authentication, authorization, gateway quotas, trusted feature retrieval, and retention controls.

## P. Audit records and their limits

The store links each event digest to the previous one and maintains a transactionally serialized chain head. SQLite uses immediate transactions with a timeout; PostgreSQL supports the durable local stack. Model version and input fingerprints help trace scores.

Normalized model inputs and the prediction are recorded. Full raw history and every contextual input are not retained, although activated findings are. This limits history duplication but prevents complete contextual replay from the audit record alone. Production needs an access-controlled event store and deliberate retention design.

Hash links offer tamper evidence, not administrator-proof immutability. Somebody able to rewrite the entire database/head can rebuild the chain. Stronger guarantees need independently anchored or signed records and suitable storage.

Vercel events are in `/tmp`, can vanish on restart, and can differ across instances. This is not a durable audit ledger. Use PostgreSQL locally to study durable operations. Do not submit real payment/customer data to the public workbench.

## Q. Drift is not accuracy

The monitor compares feature distributions against a reference using Jensen–Shannon distance and, with sufficient rows, Evidently reports. A distribution flag prompts investigation; it does not prove accuracy declined.

Accuracy needs ground-truth labels, often delayed by investigations or chargebacks. The store links labels to prediction IDs and reports performance per model version. Treating high model scores as labels would create a self-confirming loop.

Guarded retraining has a 24-hour cooldown and requires a new validated labeled dataset hash. Repeatedly fitting unchanged data cannot correct a changed population. Promotion gates still apply. Scoring a synthetic case does not retrain or promote anything.

Free Vercel does not run a continuous background monitoring worker or maintain persistent cross-instance history. The local operations stack demonstrates that workflow. Synthetic drift reports are labeled demonstrations, not observed production incidents.

## R. Reproduce the IEEE experiment on Windows

Run from the repository directory. In this workspace the raw IEEE folder is adjacent to the repository.

```powershell
uv sync --frozen --extra dev --extra ops
$env:FRAUDLINE_HOME = Join-Path (Get-Location) 'runs/ieee'

# Join, validate, build past-only history, save Parquet and lineage.
.\.venv\Scripts\python.exe -m fraudline.pipeline prepare --ieee ..\ieee-fraud-detection

# Tune only inside training time; fit, calibrate, assess, register.
.\.venv\Scripts\python.exe -m fraudline.pipeline train --tune

# Exercise the actual API using authored synthetic cases.
.\.venv\Scripts\python.exe -m scripts.test_scenarios

# Export weights and aggregate evidence, never source/reference rows.
.\.venv\Scripts\python.exe -m scripts.export_demo

# Serve this run; restart after promoting a different champion.
.\.venv\Scripts\python.exe -m uvicorn fraudline.api:app --host 127.0.0.1 --port 8014
```

Data and lineage are under `runs/ieee/data/`; models, reference, registry and reports are under `runs/ieee/artifacts/`. Those local directories are ignored. Public-safe copies go to `demo-bundle/`. Never run a synthetic demo preparation command against the IEEE run directory.

For exported-model-only serving, set `FRAUDLINE_ARTIFACTS` to the absolute `demo-bundle` path and start Uvicorn. Training extras are unnecessary for that path.

If validation fails, inspect the issue rather than dropping inconvenient rows. After a crash, remove a stale lifecycle lock only after confirming no lifecycle operation remains active. A separate run directory prevents accidental comparison/replacement of synthetic and real-data champions.

## S. Read the artifacts

`lineage.json` records rows, prevalence, hashes, seed, schema and source. SHA-256 detects changed bytes; it does not prove data truth or absence of leakage.

`model.txt` stores native LightGBM trees. `metadata.json` stores ordered feature names, weight hash, sigmoid parameters, thresholds, time splits, training parameters and gain importance. `evaluation.json` contains promotion, final, baseline and product-slice metrics. `reference.parquet` holds training-derived feature rows for local drift comparisons and is excluded from public export.

Startup checks model hash and feature order. That detects accidental mismatches, not a malicious person able to replace both metadata and weights. `.gitattributes` preserves exact model bytes across Windows/Linux; line-ending conversion would otherwise change hashes. Native libraries are binary too.

The recorded training Git revision is the revision visible at run time. A run made with uncommitted changes cannot claim clean source provenance from that hash alone. The implementation commit, commands, lockfile and execution evidence together describe the run. Reproduction should use committed source.

## T. Local operations and public hosting

Vercel serves a compact portfolio interface and Python inference. Heavy training remains local. Free quotas and service terms can change. The app requires no paid LLM, hosted geolocation service, or managed feature-store subscription.

LightGBM needs a compatible OpenMP library on Linux. `app.py` preloads the bundled compatible `libgomp.so.1`; its notices/licenses remain under `native/`. This is runtime compatibility, separate from modeling.

The bundle is pinned at process startup. Changing a local registry does not change an already deployed public instance. Export, verify, and deploy explicitly. The GitHub/Vercel Git integration or deploy hook must be configured before promising automatic Git deployments.

The optional Docker Compose stack is heavier. Its default artifact/data mounts support the earlier synthetic bootstrap. Point them at the IEEE run before using it for the real-data champion. PostgreSQL, MLflow, Grafana and Prometheus use local ports and generated credentials; do not publish credentials or expose these services broadly.

## U. The UI/UX choices

The redesign uses the installed UI/UX Pro Max guidance for a data-dense financial workbench: dark navigation rail, neutral canvas, teal interaction states, and amber/red review/block meanings. Text accompanies color so status remains understandable without color perception.

The main sequence is choose a case, inspect input, edit limited fields, analyze, inspect receipt. Detailed JSON/history are progressively disclosed. Model evidence and signal coverage stay separate so prominent scores do not hide unsupported assumptions.

The interface includes field labels, keyboard focus, touch-sized controls, disabled/loading feedback, status announcements, reduced-motion handling, and responsive layouts. On phones, scenario choices become a horizontal strip. Dense tables scroll within their container. Operations retains access to readiness, monitoring, metrics and precomputed drift exercises. No fake live payment feed or invented operational metrics are needed.

System typography with a local Fira preference avoids third-party font requests. Specific content, deliberate hierarchy, and visible provenance supply identity without another frontend framework.

## V. Verification commands

```powershell
.\.venv\Scripts\python.exe -m ruff check fraudline app.py scripts tests
.\.venv\Scripts\python.exe -m pytest -q
node --check fraudline/web/app.js
```

Checks cover training/inference compatibility, validation, audit behavior, model integrity, join fan-out, time splits, lifecycle logic, offline/online history parity, account isolation, equal/future event exclusion, and scenario controls. Unit tests do not establish external fraud accuracy.

The end-to-end report records scenario results from the loaded model. Browser checks should cover desktop/mobile, keyboard usability, errors and the complete score-to-receipt flow. See the execution report for checks actually run rather than assuming every possible device was tested.

## W. A reading path for learning

1. Read the baseline transaction in `scenarios.py`; separate current input from history.
2. Read `history.py`; manually calculate a small amount ratio.
3. Follow raw amount to log amount in `data.py:features()`.
4. Find fitting, calibration, thresholds and evaluation in `pipeline.py:_train()`.
5. Follow raw score to probability/decision in `model.py:predict()`.
6. Find impossible travel in `signals.py`; see why it changes decision, not probability.
7. Trace `api.py:score()` through enrichment, model, policy and audit.
8. Explain PR-AUC, recall and false-positive rate in your own words using Model evidence.

Change one thing at a time. Do not tune on the final holdout just to make portfolio numbers look better.

## X. Exercises to deepen understanding

- Add a huge future event to a tiny test history; confirm earlier features stay unchanged.
- Supply inconsistent travel coordinates and explain why a legitimate transaction could trigger a rule.
- Remove benchmark inputs from a synthetic case and discuss missing-input distribution shift.
- Draw a reliability diagram on a new labeled validation interval.
- Measure review volume at several thresholds before discussing staffing capacity.
- Design a trusted history retrieval interface before replacing supplied histories with live storage.

Use NumPy, pandas and the standard library where sufficient; a new dependency is not automatically a better solution.

## Y. What remains limited

This is one benchmark experiment. Anonymized fields and the entity proxy have uncertain authorization-time meaning. Relative time is not verified local time. Context is only as trustworthy as its source. Policies and costs are illustrative. No merchant, identity, disposable-domain or IP-geolocation verification service is connected.

Public hosting has ephemeral audit storage, no persistent feature store, no authentication, no continuous worker and no payment integration. Device links are a request-local relationship count. Explanations are associations. Neither a score nor a rule proves fraud.

Operational use requires trusted authorization-time data, privacy/access controls, durable history, independent temporal/external validation, customer-impact analysis, capacity-aware policy, calibration monitoring, incident procedures and human review. These are prerequisites, not capabilities this demo claims to include.

## Z. Glossary

**Feature:** numeric model input. **Label:** observed target outcome. **Inference:** applying a fitted model. **Leakage:** information unavailable at scoring time entering the experiment. **Calibration:** mapping score toward observed probability. **Threshold:** cutoff for an action. **TreeSHAP:** additive tree contribution explanations. **Chronological holdout:** later interval reserved for evaluation. **Drift:** changing input/outcome distributions. **Lineage:** data/artifact provenance. **Champion:** selected model. **Challenger:** candidate evaluated for promotion. **Pseudonymization:** replacing identifiers with repeatable substitutes without guaranteeing anonymity. **Contextual control:** explicit policy separate from learned probability.

## References and next documents

- [IEEE-CIS competition](https://www.kaggle.com/competitions/ieee-fraud-detection)
- [LightGBM Python API](https://lightgbm.readthedocs.io/en/stable/Python-API.html)
- [scikit-learn probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [scikit-learn average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)
- [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)

Read the model card, runbook and execution report alongside this guide. Code and serialized execution artifacts are the final source of truth when a general explanation is less specific.
