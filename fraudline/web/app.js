const $ = (s) => document.querySelector(s);
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pct = (n) => `${(n * 100).toFixed(1)}%`;
const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    n,
  );
const state = { cases: [], selected: null, rows: [], busy: false };
async function api(path, body) {
  const response = await fetch(path, {
    ...(body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {}),
    signal: AbortSignal.timeout(60000),
  });
  const data = await response.json();
  if (!response.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Input rejected. Check the supplied values.",
    );
  return data;
}
function notice(text) {
  $("#notice").textContent = text;
  $("#notice").hidden = !text;
}
const pages = {
  operations: [
    "Operations",
    "Watch the service and its inputs.",
    "Monitoring needs recorded traffic and delayed labels; drift alone is not accuracy.",
  ],
  investigate: [
    "Investigation",
    "Every decision has a story.",
    "Explore synthetic cases. Separate model evidence from contextual controls.",
  ],
  evidence: [
    "Model evidence",
    "Trust is built on evidence.",
    "Actual training artifacts, chronological evaluation, and a reproducible model bundle.",
  ],
  coverage: [
    "Signal coverage",
    "Know what the system knows.",
    "A clear boundary between trained patterns and explicit contextual controls.",
  ],
  learn: [
    "Learn the system",
    "From data to understanding.",
    "Follow the implementation, the decisions, and the reasons behind them.",
  ],
};
function show(view) {
  if (view === "operations") renderOperations();
  if (!pages[view]) view = "investigate";
  document
    .querySelectorAll(".view")
    .forEach((el) => (el.hidden = el.id !== view));
  document.querySelectorAll("[data-view]").forEach((el) => {
    if (el.dataset.view === view) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  $("#breadcrumb").textContent = pages[view][0];
  $("#page-title").textContent = pages[view][1];
  $("#page-description").textContent = pages[view][2];
  window.scrollTo(0, 0);
}
document.querySelectorAll("[data-view]").forEach((b) =>
  b.addEventListener("click", () => {
    location.hash = b.dataset.view;
  }),
);
window.addEventListener("hashchange", () => show(location.hash.slice(1)));
show(location.hash.slice(1));
function renderCases() {
  const q = $("#search").value.toLowerCase();
  const filtered = state.cases.filter((c) =>
    `${c.title} ${c.description}`.toLowerCase().includes(q),
  );
  $("#scenario-list").innerHTML =
    filtered
      .map(
        (c) =>
          `<button class="scenario-button" data-case="${esc(c.id)}" aria-pressed="${state.selected?.id === c.id}"><span>${String(state.cases.indexOf(c) + 1).padStart(2, "0")}</span><strong>${esc(c.title)}</strong><small>${esc(c.expected_factor || "Baseline behaviour")}</small></button>`,
      )
      .join("") || '<p class="muted">No matching scenarios.</p>';
  document
    .querySelectorAll("[data-case]")
    .forEach((b) =>
      b.addEventListener("click", () => selectCase(b.dataset.case)),
    );
}
function selectCase(id) {
  state.selected = state.cases.find((c) => c.id === id);
  const c = state.selected,
    t = c.transaction;
  $("#case-title").textContent = c.title;
  $("#case-description").textContent = c.description;
  $("#amount").value = t.amount;
  $("#device").value = t.device_type;
  $("#payload").textContent = JSON.stringify(t, null, 2);
  $("#transaction-facts").innerHTML = [
    ["ACCOUNT", t.account_id],
    ["PRIOR EVENTS", t.history.length],
    ["PRODUCT / CARD", `${t.product} / ${t.network}`],
    ["EXPECTED SIGNAL", c.expected_factor || "None"],
  ]
    .map(
      ([a, b]) => `<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`,
    )
    .join("");
  renderCases();
  $("#decision").innerHTML =
    '<div class="empty-mark">↗</div><h2>Ready to investigate.</h2><p>Analyze this case to see the model probability and contextual signals. Editing the amount or device changes this request only.</p>';
}
$("#search").addEventListener("input", renderCases);
function renderDecision(row) {
  const { result: r, input: t, title } = row;
  const max = Math.max(
    ...r.reasons.map((x) => Math.abs(x.contribution)),
    0.001,
  );
  $("#decision").innerHTML =
    `<div class="decision-top"><div><span class="eyebrow">FINAL DECISION</span><h2>${r.decision === "approve" ? "Approve" : r.decision === "review" ? "Manual review" : "Block transaction"}</h2><span class="status ${esc(r.decision)}">${esc(r.decision)}</span></div><div><div class="score-number">${(r.probability * 100).toFixed(1)}<small>%</small></div><div class="score-note">Calibrated ML probability<br>Context controls do not change this number</div></div></div><div class="probability-track"><i data-width="${r.probability * 100}"></i></div><div class="threshold-labels"><span>0%</span><span>Review ≥ ${pct(r.thresholds.review)}</span><span>Block ≥ ${pct(r.thresholds.block)}</span><span>100%</span></div><div class="decision-explainer">Model decision: <strong>${esc(r.model_decision)}</strong> · ${r.signals.length} contextual signal${r.signals.length === 1 ? "" : "s"} · Final decision takes the most restrictive outcome.</div><div class="explanation-columns"><div><h3>What influenced the model</h3><p class="muted">Top TreeSHAP contributions in raw log-odds. Associations, not causes.</p>${r.reasons.map((x) => `<div class="reason"><div class="reason-label"><span>${esc(x.label)}</span><span>${x.contribution > 0 ? "+" : ""}${x.contribution.toFixed(3)}</span></div><div class="reason-track"><i class="${esc(x.direction)}" data-width="${(Math.abs(x.contribution) / max) * 100}"></i></div></div>`).join("")}</div><div><h3>Contextual controls</h3><p class="muted">Explicit policies applied to supplied history and context.</p>${r.signals.map((x) => `<div class="signal"><strong>${esc(x.title)} · ${esc(x.decision)}</strong><p>${esc(x.evidence)}</p></div>`).join("") || '<p class="muted">No contextual control was activated.</p>'}</div></div><details><summary>Computed history features</summary><pre>${esc(JSON.stringify(r.history_features, null, 2))}</pre></details><div class="receipt-meta"><span>${esc(title)} · ${money(t.amount)}</span><span>Audit ${esc(r.prediction_id.slice(0, 14))}</span><span>${esc(r.model_version)}</span></div>`;
  document
    .querySelectorAll("[data-width]")
    .forEach((el) => (el.style.width = `${el.dataset.width}%`));
}
function renderLedger() {
  const filter = $("#filter").value;
  const rows = state.rows.filter(
    (r) => filter === "all" || r.result.decision === filter,
  );
  $("#ledger").innerHTML =
    rows
      .slice()
      .reverse()
      .map(
        (row) =>
          `<tr><td><button data-receipt="${esc(row.result.prediction_id)}">${esc(row.title)}</button></td><td>${money(row.input.amount)}</td><td>${pct(row.result.probability)}</td><td><span class="status ${esc(row.result.decision)}">${esc(row.result.decision)}</span></td><td>${row.result.signals.length}</td></tr>`,
      )
      .join("") ||
    '<tr><td colspan="5" class="muted">No matching investigations yet.</td></tr>';
  document.querySelectorAll("[data-receipt]").forEach((b) =>
    b.addEventListener("click", () => {
      const row = state.rows.find(
        (r) => r.result.prediction_id === b.dataset.receipt,
      );
      selectCase(state.cases.find((c) => c.title === row.title).id);
      $("#amount").value = row.input.amount;
      $("#device").value = row.input.device_type;
      $("#payload").textContent = JSON.stringify(row.input, null, 2);
      renderDecision(row);
    }),
  );
}
$("#filter").addEventListener("change", renderLedger);
function save(input, result, title) {
  const row = { input, result, title };
  state.rows.push(row);
  if (state.rows.length > 100) state.rows.shift();
  renderLedger();
  return row;
}
function busy(value) {
  state.busy = value;
  $("#score").disabled = value;
  $("#run-all").disabled = value;
  $("#score").textContent = value ? "Analyzing…" : "Analyze transaction ↗";
}
$("#score-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selected || state.busy) return;
  busy(true);
  notice("");
  const input = structuredClone(state.selected.transaction);
  input.amount = Number($("#amount").value);
  input.device_type = $("#device").value;
  input.transaction_id = `SYN-${Date.now()}`;
  $("#payload").textContent = JSON.stringify(input, null, 2);
  try {
    renderDecision(
      save(input, await api("/predict", input), state.selected.title),
    );
  } catch (error) {
    notice(error.message);
  } finally {
    busy(false);
  }
});
$("#run-all").addEventListener("click", async () => {
  if (state.busy) return;
  busy(true);
  notice("");
  $("#suite-result").textContent = "Scoring all synthetic scenarios…";
  try {
    const data = await api("/predict/batch", {
      transactions: state.cases.map((c) => c.transaction),
    });
    let passed = 0;
    data.predictions.forEach((r, i) => {
      const c = state.cases[i];
      const ok = c.expected_factor
        ? r.signals.some((s) => s.factor === c.expected_factor)
        : r.signals.length === 0;
      if (ok) passed++;
      save(c.transaction, r, c.title);
    });
    $("#suite-result").textContent =
      `${passed} / ${state.cases.length} expected signal checks passed. Real-world accuracy is evaluated separately on the IEEE holdout.`;
    selectCase(state.cases.at(-1).id);
    renderDecision(state.rows.at(-1));
  } catch (error) {
    $("#suite-result").textContent = "Suite could not finish.";
    notice(error.message);
  } finally {
    busy(false);
  }
});
function renderModel({ metadata: m, evaluation: e }) {
  const f = e.final_test;
  $("#stats").innerHTML = [
    [
      "TRAINING SOURCE",
      m.data_source === "ieee-cis" ? "IEEE-CIS" : "Synthetic",
      `${m.rows.toLocaleString()} labeled transactions`,
    ],
    [
      "HELD-OUT PR-AUC",
      f.pr_auc.toFixed(3),
      `${f.rows.toLocaleString()} later transactions`,
    ],
    [
      "FEATURE CONTRACT",
      String(m.features.length),
      "Shared by training and inference",
    ],
    ["RISK COVERAGE", "9 factors", "Trained features + contextual controls"],
  ]
    .map(
      ([a, b, c]) =>
        `<div><span>${esc(a)}</span><strong>${esc(b)}</strong><small>${esc(c)}</small></div>`,
    )
    .join("");
  $("#connection").textContent =
    `${m.data_source === "ieee-cis" ? "IEEE-CIS" : "Synthetic"} model ready`;
  $("#model-version").textContent = m.version;
  const metrics = [
    ["PR-AUC (average precision)", "pr_auc"],
    ["ROC-AUC", "roc_auc"],
    ["Brier score ↓", "brier"],
    ["Recall at review threshold", "recall"],
    ["False-positive rate ↓", "false_positive_rate"],
    ["Hypothetical cost / transaction ↓", "cost_per_transaction"],
  ];
  $("#model-content").innerHTML =
    `<div class="evidence-header"><div><p class="eyebrow">VERIFIED MODEL BUNDLE</p><h2>${m.model_kind === "lgb-xgb-residual" ? "LightGBM + XGBoost" : "LightGBM"}, trained on ${esc(m.data_source)}.</h2><p>${esc(e.warning)}</p></div><a href="https://github.com/hafiz-fansuri/fraudline/blob/main/fraudline/hybrid.py" target="_blank" rel="noreferrer">Open training file ↗</a></div><div class="evidence-grid"><div><h3>Chronological research interval (previously inspected)</h3><div class="table-scroll"><table><thead><tr><th>Measure</th><th>Historical logistic baseline</th><th>Current model</th></tr></thead><tbody>${metrics.map(([name, key]) => `<tr><td>${name}</td><td>${e.baseline ? e.baseline[key].toFixed(4) : "Not rerun"}</td><td>${f[key].toFixed(4)}</td></tr>`).join("")}</tbody></table></div><p class="muted">Cost uses illustrative review and false-block assumptions. Each model selects its own thresholds on calibration data. These are not measured financial savings.</p><h3>Time is part of the evaluation</h3><div class="split-bar">${Object.entries(
      m.splits,
    )
      .map(
        ([name, s]) =>
          `<span title="${esc(name)}: ${s.rows} rows" data-width="${(s.rows / m.rows) * 100}"></span>`,
      )
      .join("")}</div><div class="split-key">${Object.entries(m.splits)
      .map(
        ([name, s]) =>
          `<span>${esc(name.replaceAll("_", " "))}: ${s.rows.toLocaleString()}</span>`,
      )
      .join(
        "",
      )}</div><h3>LightGBM-stage training gain (excludes residual)</h3>${Object.entries(
      m.feature_importance_gain || {},
    )
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(
        ([key, value]) =>
          `<div class="reason-label"><span>${esc(key)}</span><span>${Math.round(value).toLocaleString()}</span></div>`,
      )
      .join(
        "",
      )}<p class="muted">Gain describes training split utility; it is not causal importance.</p></div><div><h3>Reproducibility record</h3><dl class="facts">${[
      ["Version", m.version],
      [
        "Fraud prevalence",
        m.fraud_rate === undefined
          ? "Unavailable"
          : `${pct(m.fraud_rate)} (${m.fraud_rows.toLocaleString()} rows)`,
      ],
      ["Feature schema", m.feature_schema_version || 1],
      ["Model SHA-256", m.model_sha256],
      ["Prepared data SHA-256", m.data_sha256],
      ["History semantics", m.history_semantics || "Legacy feature contract"],
      [
        "Calibration",
        `Sigmoid slope ${m.calibration.slope.toFixed(4)}; intercept ${m.calibration.intercept.toFixed(4)}`,
      ],
    ]
      .map(([a, b]) => `<div><dt>${esc(a)}</dt><dd>${esc(b)}</dd></div>`)
      .join(
        "",
      )}</dl><a class="text-link" href="/guide">Understand the training process ↗</a></div></div>`;
  $("#model-content")
    .querySelectorAll("[data-width]")
    .forEach((el) => (el.style.width = `${el.dataset.width}%`));
}
async function init() {
  busy(true);
  try {
    const [model, scenarios, factors] = await Promise.all([
      api("/api/model"),
      api("/api/scenarios"),
      api("/api/factors"),
    ]);
    renderModel(model);
    state.cases = scenarios.scenarios;
    selectCase(state.cases[0].id);
    $("#factor-grid").innerHTML = factors.factors
      .map(
        (f, i) =>
          `<article class="factor-card"><span class="number">${String(i + 1).padStart(2, "0")} / SIGNAL COVERAGE</span><h3>${esc(f.name)}</h3><span class="status ${esc(f.status)}">${f.status === "trained" ? "Trained features" : f.status === "partial" ? "Trained + contextual" : "Contextual control"}</span><p>${esc(f.description)}</p></article>`,
      )
      .join("");
  } catch (error) {
    notice(`Could not load the workbench: ${error.message}`);
    $("#connection").textContent = "Connection unavailable";
  } finally {
    busy(false);
  }
}
init();

async function renderOperations() {
  try {
    const [ready, monitor] = await Promise.all([
      api("/ready"),
      api("/api/monitoring"),
    ]);
    let drift = null;
    try {
      drift = await api("/api/drift");
    } catch {}
    $("#operations-content").innerHTML =
      `<dl class="facts"><div><dt>Readiness</dt><dd>${esc(ready.status)} · ${esc(ready.model_version)}</dd></div><div><dt>Audit storage</dt><dd>${esc(ready.audit_storage)} — public Vercel storage is temporary</dd></div><div><dt>Scheduled monitoring</dt><dd>${esc(monitor.status || "Unknown")} · ${monitor.samples || 0} recorded samples</dd></div><div><dt>Delayed-label performance</dt><dd>${monitor.performance?.status === "ready" ? `PR-AUC ${monitor.performance.pr_auc.toFixed(4)}` : "Insufficient ground-truth labels; not inferred from drift"}</dd></div></dl><h3>Synthetic drift exercise</h3><p class="muted">Precomputed synthetic populations compared with the trained model reference. A synthetic reference case may also differ from IEEE. These are not production alerts and do not trigger retraining.</p>${
        drift
          ? Object.entries(drift)
              .map(
                ([name, r]) =>
                  `<div class="signal"><strong>${esc(name)}: ${r.drifted ? "distribution difference detected" : "within reference threshold"}</strong><p>${r.samples} synthetic rows · mean prediction ${pct(r.prediction_mean)} · ${esc(r.retraining)}</p></div>`,
              )
              .join("")
          : '<p class="muted">No precomputed drift exercise is available.</p>'
      }`;
  } catch (error) {
    $("#operations-content").textContent = error.message;
  }
}
$("#refresh-operations").addEventListener("click", renderOperations);
