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
