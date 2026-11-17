# Client experience

The public homepage `/` serves the new client-facing interface. The original technical application remains at `/workbench`, with its existing model evidence, scenario suite, operations and learning views. The training model and prediction API are unchanged. This is two interfaces on one existing free deployment, not a second paid service.

Files: `fraudline/web/client.html`, `client.css` and `client.js`. No frontend framework, runtime dependency, external font or tracking script was added. `api.py` changes only the homepage file and adds the preserved workbench route. The learning guide's return link now targets `/workbench#learn`.

## Design

UI/UX Pro Max's verified Cyberpunk UI style informs the dark charcoal surface, lime action, cyan details and magenta HX signature. The implementation intentionally uses restrained glow and static SVG linework rather than glitch effects. The client workflow stays focused on examples, editable details and readable outcomes; technical model internals remain in the owner workbench.

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

## Boundaries

All checks remain educational synthetic examples; no live payment integration was added. Recent checks are not durable accounts. Public scoring records remain temporary. The owner route is a separate address, not password protection or an access-control boundary. It is omitted from public client navigation but remains directly accessible.
