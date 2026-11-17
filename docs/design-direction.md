# Risk workbench design direction

Applied skill: UI/UX Pro Max, installed at `~/.codex/skills/ui-ux-pro-max`.

The initial broad design-system search suggested a marketing hero, which did not fit an investigation tool. The narrower `data dense dashboard` style result was verified as appropriate for financial analysis and adopted. This record persists the reviewed direction rather than the unsuitable broad result.

Audience: a learner or portfolio reviewer investigating synthetic fraud cases and reading real model evidence. Core task: choose a case, inspect inputs, score, compare model and policy, trace training.

Use a dark navy rail, neutral canvas, white evidence panels, teal actions, amber review and red block. Keep text status labels alongside colors. Prefer local Fira/system typography, tabular figures, restrained borders, and progressive disclosure for JSON/history. Do not introduce external font requests or decorative charting libraries.

Desktop: scenario list beside a transaction/receipt column; evidence in two readable columns. Mobile: top navigation, horizontal case strip, stacked content and locally scrollable tables. Controls remain keyboard accessible and at least 44px high. Respect reduced motion, visible focus, field labels and status announcements.

Actual metrics must come from `/api/model`. Synthetic signal-check results must never be called classifier accuracy. Context does not inflate model probability. Show each factor's trained/contextual status and link directly to the training file and complete learning guide.
