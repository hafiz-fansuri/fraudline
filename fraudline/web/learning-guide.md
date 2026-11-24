# Unified app: learning guide from input to evidence

This guide explains the November 2026 combination of Fraudline and Proofline. Read it alongside the source files. The original single-stage learning guide remains historical background, not the current hybrid's training specification.

## A. Start with the user's job

A fraud analyst receives a payment, decides which details require investigation and records a reasoned human decision. The app supports that task through a queue and a selected-transaction receipt. It is not a bank payment gateway. A green result means no configured alert, not a guarantee that a payment is legitimate.

The old public example checker is preserved at `/checker`. Technical model evidence and monitoring remain at `/workbench`. Neither route is an authentication boundary.

## B. What comes into the system?

The transaction, earlier history and supplied context are the scoring inputs. A review question is a separate retrieval input. A label such as `isFraud` is never an inference input; it is available only in the training dataset.

| Input | Why it exists | Where it would come from in a bank |
| --- | --- | --- |
| transaction_id | Trace one review | Payment event identifier |
| amount | Detect amount patterns | Payment authorization event, in validated model currency |
| time_offset | Relative time and history windows | Bank timestamp mapping; not an invented local clock |
| product | IEEE product category | A validated bank-specific mapping or retrained feature |
| network / card_type | Card category patterns | Payment metadata |
| identity_present | Identity data availability | Checkout/identity metadata; not identity verification success |
| account_id | Group earlier activity | Pseudonymous internal account key |
| history | Velocity, amount baseline, novelty | Trusted server-side history store |
| device_type / domains / regions | Additional model proxies | Approved device/payment metadata |
| context | Explicit rule inputs | Trusted location, authentication and payee services |
| benchmark_signals | Anonymized IEEE C/D/M values | Competition-only unless a validated equivalent exists |
| question | Find relevant guidance | Analyst's plain-language question |

Only the minimum scoring fields are required by the API. Optional missing inputs reduce available evidence; handling a missing value is not proof that its omission is harmless. The history list is capped at 200 events, so it is a bounded demo rather than a complete high-volume account history store. Pseudonyms are not anonymous if someone can link them back to people.

## C. Try a complete request

Start the app using the README, then run this in another PowerShell window:

```powershell
$body = @{
  transaction = @{
    transaction_id = 'DEMO-001'; amount = 75.0; time_offset = 907200
    product = 'W'; network = 'visa'; card_type = 'debit'; identity_present = $true
  }
  question = 'What human review steps apply to this transaction?'
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/review' -Method Post -ContentType 'application/json' -Body $body
```

`risk.probability` comes from the calibrated hybrid. `risk.model_decision` comes from its thresholds. `risk.signals` lists separate contextual controls. `risk.decision` is the more severe suggestion. `investigation` contains retrieved sources and human steps; it cannot modify any risk field.

## D. Follow a request through the code

```mermaid
sequenceDiagram
    participant Analyst
    participant Desk as Browser desk
    participant API as FastAPI
    participant Model as Hybrid model
    participant RAG as Bounded retriever
    Analyst->>Desk: Select transaction
    Desk->>API: POST /api/review
    API->>API: Validate fields; derive past-only history
    API->>Model: Ordered 54-feature matrix
    Model-->>API: Calibrated probability and model suggestion
    API->>API: Evaluate controls and append audit
    API->>RAG: Question and fired factor names
    RAG-->>API: Versioned passages, citations, human steps
    API-->>Desk: Risk plus separate investigation
    Analyst->>Desk: Inspect evidence / save review
```

`fraudline/api.py` defines Pydantic models and orchestration. Unknown fields, fraud labels, nonfinite values and invalid categories are rejected. Requests are bounded by size and rate. These are demo safeguards, not authentication or distributed rate limiting.

## E. Features are transformations

A raw amount is transformed into a log amount. Relative time becomes cyclic hour features. Earlier activity becomes counts, amount ratios, novelty and time-pattern features. Email domains become buckets and mismatch indicators. All of this happens through `fraudline/data.py` and `fraudline/history.py`, shared between offline preparation and serving.

History excludes the current transaction, equal timestamps and future events. The IEEE account grouping key is a card/address proxy, not a verified person. Location, password changes and real device identifiers are absent from IEEE and therefore remain explicit contextual controls.

## F. Why modify the Kaggle code?

The supplied notebook is designed for a fixed competition train/test batch. It builds aggregate statistics on the combined batch and encodes categories together. That lets later transactions influence earlier feature values. It also selects a rank blend, whose value depends on the other rows in the batch. Neither behavior is appropriate for a stable single-payment API.

The adaptation retains the central LightGBM → XGBoost residual idea but uses the existing 54-feature serving contract. It replaces grouped folds that can see later dates with expanding-time folds. It saves both model stages and calibration. There is no claim of reproducing the notebook's 488-feature metrics.

## G. Where exactly does training happen?

Open **`fraudline/hybrid.py`**, function **`train()`**. It:

1. Loads a prepared parquet dataset and verifies its SHA-256 against `lineage.json`.
2. Creates chronological training, calibration, comparison and later research partitions.
3. Trains three past-only LightGBM folds to make out-of-fold training margins.
4. Fits the final LightGBM on the training partition.
5. Fits XGBoost on the later training rows with out-of-fold margins as `base_margin`.
6. Fits logistic calibration and chooses thresholds on calibration only.
7. Saves native artifacts and evaluates the later partitions.

The first training prefix has no past-trained prediction; it is excluded from residual fitting. The final base model sees more training data than early fold models. That distribution difference is a remaining limitation of this residual design and must be assessed on new institution-specific validation data.

The earlier `fraudline/pipeline.py` trains a separate single-stage model, prepares data and supports existing lifecycle tooling. Running its `train` command does not create the new hybrid.

## H. What are raw margins and residual boosting?

A binary tree model can output log-odds, an unbounded number that becomes a probability after a sigmoid. LightGBM supplies the starting log-odds. XGBoost receives that value as `base_margin` and learns an adjustment. At serving time, the same saved LightGBM supplies the margin to the same saved XGBoost model.

The calibrator learns a slope and intercept on separate calibration rows. The calibrated value is `sigmoid(slope × hybrid_margin + intercept)`. Thresholds convert that estimate into a model suggestion. A probability is a statistical estimate under this dataset and calibration, not a verified fact about a customer.

## I. What files does training save?

| File | Purpose |
| --- | --- |
| model.txt | Native LightGBM trees, byte-preserved in Git |
| residual.ubj | Native XGBoost residual model, treated as binary |
| metadata.json | Exact feature order, artifact hashes, calibration, thresholds, folds, splits and lineage |
| evaluation.json | Executed research metrics and the warning about reused intervals |

`fraudline/model.py` verifies hashes and feature order before serving. It does not load a pickle. Current explanations show **LightGBM-stage contributions only**; they exclude the residual model and are explicitly labeled. They must not be presented as a complete hybrid SHAP explanation or causal explanation.

## J. How to retrain safely

Follow the README preparation and hybrid commands. Use a new output directory. Raw CSVs, prepared parquet, references, local databases and environment secrets remain ignored and outside the public bundle.

The hybrid command does not automatically promote a model. To test one locally without changing the public champion, call `create_app(model_path=Path(...))` or create an isolated artifacts directory with `models/<version>` and a `registry.json` containing that champion. Set `FRAUDLINE_ARTIFACTS` to that isolated directory before starting the API. `/api/model` additionally needs that model's evaluation file.

For an intentional owner release: verify results and bundle integrity, update the private registry with a documented decision, and run `python -m scripts.export_demo` using that private artifacts directory. The exporter includes both stages but excludes raw/reference rows. It removes stale public model directories inside `demo-bundle/models`, so preserve needed historical reports first. Do not silently compare synthetic and real-data populations or publish a model solely because the final research score looks appealing.

The November hybrid was intentionally selected to implement the user's architecture, not automatically promoted by the older performance gate. Its deployment reason is recorded in the committed registry. The previous native bundle remains available as historical evidence and rollback material.

## K. Results and honest comparisons

The new CPU run uses 300 rounds and two threads. On the 88,081-row later interval it produced average precision 0.46008, ROC-AUC 0.87565, Brier 0.02457, recall 0.78467 and false-positive rate 0.18681 at its calibrated review threshold. The previous single-stage model's average precision was 0.46145. The hybrid does not demonstrate an accuracy improvement.

These intervals were already inspected during the earlier project. Calling the new results an untouched test would be wrong. A bank-specific evaluation must reserve genuinely new temporal data, define operational costs and capacity, check segments and missing inputs, and examine calibration and false-positive burden. Synthetic scenarios test software behavior, not detection accuracy.

## L. What was reused from Proofline?

Proofline's application is evidence-first RAG for AI-security questions. Its JavaScript core provides reciprocal rank fusion, source diversity, citation checks and evaluation helpers. The unified app ports the relevant ideas into `fraudline/investigation.py` and includes MIT attribution in `docs/PROOFLINE-NOTICE.md`.

The original OWASP corpus was not repurposed as fraud policy. Supabase, gte-small embeddings and OpenRouter are not required here. The local corpus is small enough for transparent keyword retrieval and an explicit factor-matching ranking channel. This is not semantic vector search.

## M. How does the bounded investigation work?

The server inspects the scored transaction's fired control factors, retrieves playbooks using the question and factors, combines ranked results using `1 / (40 + rank)`, and returns up to five unique sources. Each playbook is one document/passage, so source duplication cannot crowd out the set. Broad default questions return general human-review guidance rather than unrelated risk warnings.

Answers are extractive: the returned prose is copied from selected authored playbooks with numbered references. Suggested steps are also authored alongside those passages. This is an auditable retrieval-and-answer workflow, **not a free-form LLM agent**. No external provider receives transaction data or questions. It has only three fixed steps: inspect, retrieve and validate citations. It cannot execute transfers, block accounts, change policies or invoke arbitrary tools.

Each source includes a title, local URL, version, publisher and passage hash. Unsupported questions with no matching factor/evidence abstain. Fired factors can still provide relevant case evidence even when the question itself is unsupported; the UI presents this as guidance, not an answer to every possible question. Citation checks validate reference IDs only; they do not prove relevance or legal correctness.

## N. Why no external language model by default?

The smallest useful integration provides sources and review steps without a model key, paid fallback, unpredictable free-provider availability or transmission of financial details. Adding generative answers later should be an explicit, institution-approved choice with data minimization, provider controls, bounded tools, evidence-grounded output checks and measured answer quality. Existing Proofline generation code is a reference, not a production banking connector.

## O. How do imports work?

The browser reads a JSON object containing `transactions`. It checks size, count and unique IDs, then sends the batch to the API's authoritative typed validator. If any record is invalid, the queue remains unchanged. Successful validation also scores and writes audit entries. Selecting an imported record creates another scored review. This makes the demo transparent but is not idempotent ingestion.

UI results and imported records stay in browser memory until reload. **Save review** downloads the current assessment and retrieved evidence; it does not archive a customer case in a permanent system. Never import real banking data into the public demo.

## P. What is stored?

The browser holds the queue and cached results in memory. The server's existing audit store records scoring inputs/features and model results using hash-linked events. Vercel's `/tmp` SQLite can disappear or differ between instances. A hash chain does not solve durability, authorization, tamper resistance against an administrator or tenant isolation. Local PostgreSQL is optional in the existing Docker stack.

Playbooks are versioned with the application. Replacing them requires an owner code release; there is no public policy upload or policy-edit endpoint. Questions and generated investigation responses are not written to an external RAG database.

## Q. Frontend design choices

The interface keeps the approved charcoal, lime, cyan and subtle HX identity. The operator's primary surface is a ledger next to a receipt. Search and a status filter reduce navigation; the details disclosure keeps thresholds and technical caveats available without dominating the task. Source passages are expandable and review suggestions include text, not just color. Mobile stacks the queue above the receipt.

The same Impeccable and UI/UX Pro Max skills informed hierarchy, accessible controls, contrast and responsive layout. Fonts are self-hosted. There are no invented live transaction counters, fabricated savings or decorative charts presented as evidence.

## R. Verification and CI/CD

`tests/test_investigation.py` checks rank fusion, unsupported-question abstention, allowed investigation steps, saved hybrid reload, one-record/batch parity, artifact tampering, timestamp fold boundaries, the review endpoint and label rejection. Existing suites check data contracts, history, controls, audit and lifecycle behavior. `scripts/test_scenarios.py` exercises all eleven authored cases through the actual serving path.

GitHub Actions runs lint, tests, synthetic serving verification, pipeline smoke checks, runtime dependency audit and a Docker build. Optional operations dependency findings are recorded separately. Vercel deployment is an explicit CLI release unless a deploy hook is configured. A successful GitHub push alone is not proof that production changed.

## S. Reading order for the code

Start with `fraudline/web/desk.html` and `desk.js`, then `api.py` (`Transaction`, `Review`, `score`, `/api/review`). Next read `history.py`, `data.py`, `model.py` and `hybrid.py`. Finish with `investigation.py`, `store.py`, tests and `.github/workflows/ci.yml`. The source is intentionally one FastAPI app rather than two independent backends with a second frontend build.

## T. Troubleshooting

- **Model unavailable:** check artifact path, champion registry and hashes. Do not disable integrity checks.
- **Input rejected:** compare required fields, numeric types and enums with `/openapi.json`; use the downloaded synthetic example.
- **No evidence:** revise the question to the supported playbooks; an abstention is preferable to invented guidance.
- **Unexpected review:** separate model threshold behavior from contextual escalation; inspect missing inputs and the supplied past history.
- **Old page after deployment:** verify asset version, deployment alias and served model version before assuming a training problem.
- **Training dependency missing:** install the locked `train` or `dev` extras; the lean serving environment intentionally excludes training tools.

## U–Z. Before a real institution uses it

Use a bank-specific model and feature availability contract; approved internal policies with owners and effective dates; authenticated staff accounts, roles and tenant isolation; a trusted history store; idempotent ingestion; encrypted durable audit and retention controls; a fresh temporal validation dataset; monitored service performance and rollback; and an approved human decision process. These are future integration requirements, not completed features or claims of regulatory compliance.

The core separation should remain: **the detector estimates risk, controls flag context, retrieval supplies evidence, and authorized humans decide consequential actions.**
