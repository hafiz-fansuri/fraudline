# Unified release verification — 24 November 2026

- Executed local IEEE hybrid training: three expanding-time folds, final LightGBM and XGBoost residual, 300 rounds, two CPU threads. Native reload verified. Published model `fl-hybrid-20261124-final`.
- Full pytest suite: **33 passed**. One upstream FastAPI/Starlette TestClient deprecation warning; no test failures.
- Ruff: passed across application, scripts and tests. JavaScript syntax check passed.
- Served hybrid synthetic API scenarios: **11/11 passed**. These test controls and serving, not classifier accuracy.
- Runtime dependency audit of the complete pinned inference requirements: **no known vulnerabilities found**. Used `--no-deps --disable-pip` after Windows temporary-environment cleanup locking interrupted the normal requirements audit. CI retains the normal audit on Linux.
- Browser: desktop 1440px and mobile 375px, no horizontal page overflow. Search and status filters, real synthetic scoring, travel escalation, template download, JSON import and unsupported-question abstention checked. The preserved workbench displays the hybrid metrics and training link.
- Screenshot `docs/unified-desk.jpg` records the working desktop app, not a generated mockup.
- Impeccable detector ran once. It could not resolve the API-served `/assets/desk.css` path and reported a flat-type-hierarchy warning from assumed 16px defaults. Browser-computed desktop h1 was 61.92px; body 16px. Manual rendered inspection checked hierarchy instead of treating the unresolved stylesheet warning as a measured defect.
- Raw IEEE CSV/parquet, private runs, databases, references and environment secrets remain excluded from Git and Vercel uploads. Only native model artifacts and aggregate evidence are exported.

## Limits

No production bank integration, authentication, tenant isolation, durable hosted case storage or payment action exists. The playbooks are illustrative and the RAG workflow is local/extractive, not an autonomous LLM agent. No operational banking load test or fresh unseen-bank validation has been performed. Existing research intervals have been inspected before; the hybrid does not establish improved accuracy over the earlier model.
