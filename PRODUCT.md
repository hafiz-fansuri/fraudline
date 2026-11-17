# Fraudline
<!-- impeccable:product-schema 1 -->

## Platform
web

## Product Purpose
A fraud-screening demonstration with two separate audiences. The public client experience at `/` explains synthetic transaction checks in plain language. The owner's technical workbench remains at `/workbench` for model evidence, training, scenarios and operations. The trained IEEE-CIS model is shared; no raw competition rows are public.

## Users
Clients or nontechnical visitors exploring a guided risk check; recruiters evaluating the engineering; the project owner investigating predictions and operating the local stack.

## Capabilities and Constraints
Free services only. FastAPI with a custom investigation UI. Full operations run locally; hosted demo must not expose lifecycle mutation endpoints. Claims must come from executed training and checks. A synthetic model is not evidence of real payment fraud detection performance.

## Evidence on Hand
Executed IEEE training/evaluation, 54 model features, synthetic operational cases, and aggregate model evidence. No live customer payment integration or measured production savings.

## Product Principles
Expose provenance; explain model behavior without causal claims; keep invalid and unavailable states explicit; preserve the final chronological test interval.
