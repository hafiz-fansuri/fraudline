# Client experience

The public homepage `/` serves the new client-facing interface. The original technical application remains at `/workbench`, with its existing model evidence, scenario suite, operations and learning views. The training model and prediction API are unchanged. This is two interfaces on one existing free deployment, not a second paid service.

Files: `fraudline/web/client.html`, `client.css` and `client.js`. Sora is self-hosted under `web/fonts/` with its OFL license. No frontend framework, runtime package, third-party font request or tracking script was added. The original routing change in `api.py` preserves the workbench; the 19 November refinement does not change the API. The learning guide's return link targets `/workbench#learn`.

## Design

The dark charcoal, lime action, cyan detail and magenta HX identity originated with UI/UX Pro Max. The user approved an Impeccable desktop/mobile preview on 19 November 2026: bolder Sora lettering, a checker in the first desktop viewport and cleaner surfaces. The ornamental radar and decorative section labels are removed. The client workflow stays focused on examples, editable details and readable outcomes; technical model internals remain in the owner workbench.

## Useful interactions

- Four starting examples plus all eleven scenarios in a native selector.
- Editable amount, device and optional purchase/account context, retaining clearly labeled example history.
- Plain-language outcomes, separate model probability, warning explanations and suggested next steps.
- Old result cleared on input changes; no fabricated result on failed requests.
- Three recent checks in browser memory only, with input and receipt restored together.
- Downloadable plain-text summary with outcome, evidence, next step, model version and reference.
- Native FAQ disclosures, keyboard focus, status announcements and reduced-motion styles.
- Small HX monogram in the footer, with magenta styling and an accessible label.

## Executed checks

30 regression tests passed, including assertions that `/` serves the client assets and `/workbench` still serves the original application. Ruff and JavaScript syntax checks passed. The real model remains `fl-20261117072348-496b08`.

Browser checks: everyday example suggested no added review; the travel example suggested pause and displayed country/travel evidence. A summary downloaded successfully and its text was inspected. Editing the amount cleared the stale receipt. A recent check restored the original amount/example and receipt. The FAQ opened correctly, and the owner workbench loaded its IEEE evidence.

Responsive checks at 1440px desktop, 375px phone and 812px landscape passed. Phone and landscape had no page-wide horizontal overflow. A mobile text-joining issue caused by hidden line breaks was corrected. The HX footer mark was visually inspected. See `client-desktop.jpg` for the client design.

Measured text contrast on dark surfaces: primary 16.09:1, secondary 8.09:1, cyan 12.35:1, lime 15.51:1; the primary-button text pair is 14.44:1. Control boundaries are 3.8:1. These checks do not constitute a complete accessibility certification. Network failure messaging was implemented but not separately fault-injected in the browser.

## Approved refinement verification — 19 November 2026

30 regression tests passed again, along with JavaScript syntax checking. All 27 static client selectors and unique element IDs were checked after the layout move. The original technical workbench HTML, CSS, JavaScript, backend and model artifacts have no changes in this refinement.

Browser acceptance covered 1440px desktop and 375px phone, with no page-wide horizontal overflow. The self-hosted display renders at 86.4px on the desktop check. The everyday example returned 1.7% and no added review; the travel example returned 1.9% and pause/verify. Editing the amount cleared its prior receipt. The disclosure exposes all eleven cases. Mobile navigation opens, closes after selecting a link and supports Escape. The updated screenshot reflects the implemented page, with an empty initial result rather than a fabricated sample prediction.

Impeccable's mechanical detector ran once. It could not resolve `/assets/client.css` through the FastAPI mount and consequently reported a false flat-type warning; the actual computed typography was verified in the browser. Its other warning flagged retained, approved educational copy. No detector configuration or unrelated design context was repaired. This was a bounded desktop/mobile pass, not an accessibility certification or a new model assessment.

## Boundaries

All checks remain educational synthetic examples; no live payment integration was added. Recent checks are not durable accounts. Public scoring records remain temporary. The owner route is a separate address, not password protection or an access-control boundary. It is omitted from public client navigation but remains directly accessible.
