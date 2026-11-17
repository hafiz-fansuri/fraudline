# Fraudline interface

## Client experience (current public entry)

`/` serves a distinct client-facing site in `web/client.html`, `client.css` and `client.js`. Keep the existing technical workbench at `/workbench`. A separate route is not authentication or a private admin security boundary.

UI/UX Pro Max searches: the broad design-system result recommended Swiss minimalism and a marketing hero, which was unsuitable as a complete transaction workflow. A narrower verified `cyberpunk-ui` style result matches the user's explicit neon-on-dark request. Apply its dark surfaces and accent vocabulary with minimal motion and readable typography; omit glitch/scanline effects that would distract clients.

Use charcoal #0b0f12, raised panels #11171b, readable ivory #f0f3e9, secondary #a4b0ae, lime #c8ff78 actions, cyan #72e8e2 contextual detail, and a small magenta #ee8cd4 HX signature in the footer. Amber/red are semantic review/pause colors, always paired with text. Restrict glow to the authored SVG diagram and signature. No external fonts, UI framework, fake telemetry or marketing performance claims.

Primary task: choose a clearly synthetic example, edit its details, check it, read a plain-language outcome/reasons/next step, optionally save a text summary. Preserve an example's context/history through the existing prediction API. Clear stale results when details change. Recent checks remain browser-memory-only and max three. Show unavailable states without fabricated scores.

Desktop: generous hero and signal diagram; input/result panels side by side. Mobile: navigation and one-column flow; remove the decorative diagram, keep all essential controls and readable results. Use labeled native controls, visible focus, touch targets, status announcements, reduced-motion support, intrinsic wrapping and internal overflow only where needed. Root uses its own CSS/JS so the owner workbench remains visually separate.

## Original workbench design record

Operate mode. The approved transaction-investigation concept uses a ledger beside a decision receipt. One selected transaction drives the receipt; replay, model evidence and drift remain distinct tasks.

White and neutral #f7f7f8 surfaces; dark ink, #002fa7 selection and primary actions. Amber means review; red means block or drift alert. Helvetica Neue/Helvetica/Arial provides one typographic family, tabular figures and a restrained editorial scale. No ornamental gradients, fictional telemetry or metric-card wall.

Desktop: capped 1536px content with 44px gutters, a horizontal task navigation and an asymmetric two-column ledger/receipt. Mobile: 20px gutters, a bounded scrolling transaction list and the receipt below. Selected rows have a pale blue background. The receipt exposes actual model probability, two thresholds, raw-score contributions and an audit reference.

Every number is fetched from the trained model, generated synthetic transactions or computed reports. Replay is labeled synthetic. Errors show unavailable state; no fabricated fallback scores. Drift injection switches between precomputed scenarios and explicitly does not retrain.

Controls have visible keyboard focus; replay pauses on hidden tabs and navigation. Motion is a single brief view transition, disabled for reduced-motion preference. All tokens live at :root in fraudline/web/style.css.
