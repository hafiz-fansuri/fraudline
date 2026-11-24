# Fraudline
<!-- impeccable:product-schema 1 -->

## Platform
web

## Unified product update — 24 November 2026

The public entry `/` combines Fraudline scoring with Proofline-inspired cited investigation for an analyst reviewing synthetic or imported transactions. `/checker` preserves the client checker; `/workbench` preserves technical evidence. Native LightGBM + XGBoost residual serving uses 54 shared features. Investigation retrieves local playbooks and supports user-triggered OpenRouter answers through a dedicated Supabase function using the server-side RAGS key. Generation shares only the question, minimal status/probability summary and selected playbooks, with a visible privacy notice. Local extractive guidance remains the fallback. No bank connection, staff authentication, tenant isolation or payment actions exist. All policies are illustrative and current evaluation intervals were previously inspected.

## Product Purpose (original project context)
A fraud-screening demonstration with two separate audiences. The public client experience at `/` explains synthetic transaction checks in plain language. The owner's technical workbench remains at `/workbench` for model evidence, training, scenarios and operations. The trained IEEE-CIS model is shared; no raw competition rows are public.

## Users
Clients or nontechnical visitors exploring a guided risk check; recruiters evaluating the engineering; the project owner investigating predictions and operating the local stack.

## Capabilities and Constraints
Free services only. FastAPI with a custom investigation UI. Full operations run locally; hosted demo must not expose lifecycle mutation endpoints. Claims must come from executed training and checks. A synthetic model is not evidence of real payment fraud detection performance.

## Evidence on Hand
Executed IEEE training/evaluation, 54 model features, synthetic operational cases, and aggregate model evidence. No live customer payment integration or measured production savings.

## Product Principles
Expose provenance; explain model behavior without causal claims; keep invalid and unavailable states explicit; preserve the final chronological test interval.
