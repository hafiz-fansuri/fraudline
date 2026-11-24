> **OpenRouter update:** Ask assistant now calls a dedicated Supabase function using the stored RAGS key. The local/extractive descriptions below explain the fallback path. Read [the current assistant, privacy and status reference](openrouter-assistant.md) for generation, data sharing, quotas and status meanings.

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


# OpenRouter assistant and status explanations

## What changed

The transaction desk now has **Ask assistant**, using the existing server-side `RAGS` OpenRouter key in the `proofline-ai-security` Supabase project. The new `fraudline-assistant` Edge Function is separate from the original Proofline function. It keeps JWT verification enabled and calls only free model IDs, with zero prompt/completion price ceilings. No paid fallback is enabled.

Selecting a transaction still uses local scoring and local playbooks only. OpenRouter is called **only when the user submits a question**. General questions are supported, but a language model cannot guarantee an answer to every question. Unsupported bank-policy conclusions must be identified as unsupported.

## Data flow and privacy

```mermaid
sequenceDiagram
    participant User
    participant Desk
    participant API as FastAPI
    participant Edge as Supabase assistant
    participant AI as OpenRouter free model
    User->>Desk: Ask a question
    Desk->>API: Transaction and question (existing review API)
    API-->>Desk: Unchanged risk assessment and retrieved playbooks
    Desk->>Edge: Question, evidence IDs, probability and status labels
    Edge->>Edge: Resolve canonical passages; claim daily quota
    Edge->>AI: Question, minimal assessment and canonical passages
    AI-->>Edge: Plain-language answer
    Edge->>Edge: Validate citation IDs
    Edge-->>Desk: Cited answer or general explanation
```

Automatically shared: the user's question, calibrated probability, model/final status labels and selected illustrative playbooks. **Not automatically shared:** transaction ID, amount, account ID, device, precise location or history. A user can still type sensitive details into a question, so the UI explicitly says not to enter personal or confidential information. Questions pass through Supabase and OpenRouter/model providers; do not assume provider retention is disabled. This is not an approved banking-data processing arrangement.

The OpenRouter secret is never copied into Git, Vercel or the browser. `fraudline/web/rags-config.json` contains public Supabase connection identifiers and a legacy public `anon` gateway JWT, as in Proofline; it is not an OpenRouter or service-role key. Public demo access is quota-limited, not staff authentication.

## How answers are built

The local retriever selects up to five versioned playbooks. The Edge Function accepts only their known IDs and resolves their canonical text from its own bundled corpus. It does not accept caller-written passages. It strips the assessment to three fields before building the prompt. The prompt asks the model to separate general knowledge from passage-supported case or policy claims, cite only supplied sources, state uncertainty and never take actions.

The selected free model is `FRAUDLINE_OPENROUTER_MODEL` if configured, otherwise `inclusionai/ling-3.2-flash:free`. A single bounded fallback uses `particle-ai/particle-1:free`. Only IDs ending in `:free` or `openrouter/free` are accepted. Each attempt has a 25-second timeout and an output limit. A shared database quota allows **30 assistant requests per day** (OpenRouter/model-provider limits may be lower) for this public app. A request can use up to two free model attempts. The existing Proofline quota is separate.

With retrieved evidence, answers must include at least one in-range numbered citation. Without evidence, the UI labels the response **General explanation · not bank policy**, and invented numbered citations are rejected. Citation ID checks do not prove that a source supports a claim. General knowledge in an otherwise cited answer is still model-generated and needs human verification.

Generation failures, empty responses, invalid citations, timeouts and exhausted quotas show **AI unavailable**. The score, controls and local playbooks remain visible. The user can retry. The model does not change probability, status, policy or money movement. Output is rendered as escaped plain text; HTML, scripts and remote images are not executed.

## Transaction status meanings

| Status | Explanation | Next step |
| --- | --- | --- |
| Not checked | No scoring assessment yet | Select the transaction |
| No alert | Model below review threshold and no contextual escalation | Follow normal checks; this is not a guarantee of safety |
| Review suggested | Model threshold or contextual signal calls for verification | A person reviews details and evidence |
| Pause suggested | High model estimate or a strong control warning | Escalate through the institution's process; the app has not blocked funds |
| Review unavailable | Scoring could not complete | Check the service/input and retry; no substitute score is shown |

The selected status has its explanation immediately below the label. The queue also includes an expandable guide explaining every status. Model suggestion and final contextual suggestion remain separate.

## Assistant status meanings

- **AI answer · playbooks cited:** generated answer with valid reference IDs; check the actual passages.
- **General explanation · not bank policy:** answer without retrieved support; not a case-specific or regulatory conclusion.
- **Writing your answer:** request is in progress; risk findings remain unchanged.
- **AI unavailable:** free service/quota/citation/network problem; local guidance remains available.

## Files and verification

- `supabase/functions/fraudline-assistant/index.ts`: secret access, quota and provider calls.
- `supabase/functions/fraudline-assistant/core.mjs`: input allowlist, prompts and citation checks.
- `supabase/functions/fraudline-assistant/corpus.json`: versioned canonical playbooks; regenerate from `fraudline.investigation.sources()` when changing the corpus, then redeploy both sides.
- `fraudline/web/desk.js`: explicit question submission, AI state, escaped rendering and status explanations.
- `tests/assistant.test.mjs`: payload minimization, canonical evidence, free-only models, citation bounds and invalid inputs.

Run `node --test tests/assistant.test.mjs`, `uv run pytest -q` and `uv run ruff check fraudline app.py tests scripts`. The JavaScript tests are included in GitHub Actions. Serving, retrieval and hybrid-model tests remain in the Python suite. Free-provider availability changes independently of code releases; a successful smoke test is not a reliability guarantee.

## Deployment

Deploy the dedicated function to the existing Supabase project with JWT verification enabled. The project already holds `RAGS` and the service-role-only `claim_budget` RPC; no new table or permission grant is required. Deploy the frontend/FastAPI separately to Vercel. The OpenRouter key remains in Supabase secrets. User approval for this project and the described data sharing was obtained before function deployment.

Provider references: [OpenRouter API](https://openrouter.ai/docs/api_reference/overview), [Supabase secrets](https://supabase.com/docs/guides/functions/secrets).
