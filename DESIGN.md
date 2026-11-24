# Unified analyst desk — 24 November 2026

Operate mode at `/`, implemented in desk.html, desk.css and desk.js. Inherit the established charcoal/lime/cyan/Sora/HX language. Task-first transaction ledger and receipt, searchable and filterable, with progressive disclosure of model details and cited playbooks. Stack on mobile with bounded queue scroll. Import/export are JSON and synthetic-only. The original client design below is retained at `/checker`; technical workbench remains `/workbench`.

# Fraudline interface

## Client experience (current public entry)

`/` serves a distinct client-facing site in `web/client.html`, `client.css` and `client.js`. Keep the existing technical workbench at `/workbench`. A separate route is not authentication or a private admin security boundary.

Approved client refinement, 19 November 2026: implement the Impeccable desktop/mobile mockup with a dominant three-line headline and the working checker beside it in the first viewport. Keep the dark/neon identity and HX mark. Remove the radar ornament, decorative eyebrows and numbered section labels. Preserve all checking, context, recent-history and download behavior.

Use charcoal #0b0f12, raised panels #11171b, readable ivory #f0f3e9, secondary #a4b0ae, lime #c8ff78 actions, cyan #72e8e2 contextual detail, and a small magenta #ee8cd4 HX signature in the footer. Amber/red remain semantic review/pause colors paired with text. Self-host Sora with its OFL license; no third-party font requests. Display weight 750, tracking no tighter than -0.04em, generous separation, flat fills and one bordered checker surface. No ornamental glow, gradients, UI framework, fabricated telemetry or performance claims.

Primary task: choose a clearly synthetic example, edit its details, check it, read a plain-language outcome/reasons/next step, optionally save a text summary. Preserve an example's context/history through the existing prediction API. Clear stale results when details change. Recent checks remain browser-memory-only and max three. Show unavailable states without fabricated scores.

Desktop: headline/CTA on the left; one coherent checker on the right with inputs followed by real result content behind a separator. Show a three-step process strip below. Mobile: compact navigation with an accessible disclosure button and Escape support, stacked intro/checker, full-width presets and fields on small phones. All eleven cases remain in an explicit disclosure; context and history remain available without dominating the form. The initial result is honestly empty, never the mockup's fixed sample score. Theme selection, caret, focus and scrollbars; retain reduced motion and labeled native controls. Root uses its own CSS/JS; the owner workbench is untouched.

## Original workbench design record

Operate mode. The approved transaction-investigation concept uses a ledger beside a decision receipt. One selected transaction drives the receipt; replay, model evidence and drift remain distinct tasks.

White and neutral #f7f7f8 surfaces; dark ink, #002fa7 selection and primary actions. Amber means review; red means block or drift alert. Helvetica Neue/Helvetica/Arial provides one typographic family, tabular figures and a restrained editorial scale. No ornamental gradients, fictional telemetry or metric-card wall.

Desktop: capped 1536px content with 44px gutters, a horizontal task navigation and an asymmetric two-column ledger/receipt. Mobile: 20px gutters, a bounded scrolling transaction list and the receipt below. Selected rows have a pale blue background. The receipt exposes actual model probability, two thresholds, raw-score contributions and an audit reference.

Every number is fetched from the trained model, generated synthetic transactions or computed reports. Replay is labeled synthetic. Errors show unavailable state; no fabricated fallback scores. Drift injection switches between precomputed scenarios and explicitly does not retrain.

Controls have visible keyboard focus; replay pauses on hidden tabs and navigation. Motion is a single brief view transition, disabled for reduced-motion preference. All tokens live at :root in fraudline/web/style.css.
