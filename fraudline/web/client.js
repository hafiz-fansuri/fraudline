const $ = (selector) => document.querySelector(selector);
const state = {
  cases: [],
  selected: null,
  recent: [],
  active: null,
  busy: false,
};
const emptyResult = $("#result-content").innerHTML;
const escapeHTML = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    value,
  );
const percent = (value) => `${(value * 100).toFixed(1)}%`;
const icons = {
  normal: '<path d="M4 8h16v12H4zM8 8V6a4 4 0 0 1 8 0v2"/>',
  amount: '<path d="m4 17 6-6 4 3 6-9M14 5h6v6"/>',
  "new-device":
    '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4"/>',
  "impossible-travel":
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a18 18 0 0 1 0 18 18 18 0 0 1 0-18"/>',
};
const exampleLabels = {
  normal: "Everyday purchase",
  amount: "Unusual spending",
  "new-device": "A new device",
  "impossible-travel": "Unusual travel",
};
const decisionCopy = {
  approve: {
    label: "No added review",
    title: "No extra review suggested.",
    description:
      "The model is below its review threshold, and no contextual check has raised a warning.",
    next: "No additional check is suggested by this example. A low estimate is not a guarantee: verify anything unexpected using a trusted channel.",
  },
  review: {
    label: "Review recommended",
    title: "Take a closer look.",
    description:
      "Something in this example deserves another check before you draw a conclusion.",
    next: "Confirm the transaction with the account holder through a trusted channel. Check the amount, device and any recent account changes before proceeding.",
  },
  block: {
    label: "Pause and verify",
    title: "Pause this transaction.",
    description:
      "The model or an explicit check has raised a strong warning. Verify the details before proceeding.",
    next: "Pause the transaction in a real review workflow and verify the account holder and activity through a trusted channel. This demo does not stop a real payment.",
  },
};

async function api(path, payload) {
  const response = await fetch(path, {
    signal: AbortSignal.timeout(45000),
    ...(payload
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      : {}),
  });
  if (!response.ok) {
    if (response.status === 429)
      throw new Error(
        "A few too many checks were requested. Please wait a minute and try again.",
      );
    if (response.status === 422)
      throw new Error(
        "Some details could not be checked. Choose an example again, then review the amount and device.",
      );
    throw new Error(
      "The checking service is temporarily unavailable. Your example has not been scored. Please try again.",
    );
  }
  return response.json();
}

function svg(content) {
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${content}</svg>`;
}
function resetResult() {
  state.active = null;
  $("#result-panel").className = "result-panel";
  $("#result-content").innerHTML = emptyResult;
  $("#result-state").textContent = "AWAITING A CHECK";
}
function setBusy(busy) {
  state.busy = busy;
  $("#details-fieldset").disabled = busy;
  $("#example-fieldset").disabled = busy;
  $("#all-examples").disabled = busy;
  $("#result-panel").setAttribute("aria-busy", String(busy));
  $("#analyze").innerHTML = busy
    ? "Looking at the signals…"
    : `Check this example ${svg('<path d="M5 12h14M13 6l6 6-6 6"/>')}`;
  document.querySelectorAll(".recent-button").forEach((button) => {
    button.disabled = busy;
  });
}
function fillDetails(transaction) {
  $("#client-amount").value = transaction.amount;
  $("#client-device").value = transaction.device_type || "unknown";
  $("#client-merchant").value =
    transaction.context?.merchant_category || "general";
  $("#client-payee").checked = Boolean(
    transaction.context?.new_payee && transaction.context?.withdrawal,
  );
  $("#client-password").checked =
    transaction.context?.password_changed_minutes != null &&
    transaction.context.password_changed_minutes <= 30;
}
function selectExample(id) {
  if (state.busy) return;
  state.selected = state.cases.find((item) => item.id === id);
  if (!state.selected) return;
  const transaction = state.selected.transaction;
  fillDetails(transaction);
  $("#all-examples").value = id;
  $("#example-description").textContent = state.selected.description;
  const history = transaction.history.filter(
    (event) =>
      event.account_id === transaction.account_id &&
      event.time_offset < transaction.time_offset,
  );
  $("#history-count").textContent =
    `${history.length} earlier example transactions`;
  $("#history-description").textContent =
    "Synthetic activity from the same example account.";
  document
    .querySelectorAll("[data-example]")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.example === id),
      ),
    );
  $("#score-error").hidden = true;
  $("#amount-error").hidden = true;
  $("#client-amount").removeAttribute("aria-invalid");
  resetResult();
}

function renderFindings(result) {
  const check = svg('<path d="m5 12 4 4L19 6"/>');
  const warning = svg('<path d="m12 3 10 17H2zM12 9v4M12 16h.01"/>');
  if (!result.signals.length)
    return `<div class="finding">${check}<div><strong>No additional warning signals</strong><p>The supplied example history and contextual checks did not raise a warning. The model estimate is still considered separately.</p></div></div>`;
  return result.signals
    .map(
      (signal) =>
        `<div class="finding">${warning}<div><strong>${escapeHTML(signal.title)}</strong><p>${escapeHTML(signal.evidence)}</p></div></div>`,
    )
    .join("");
}

function renderResult(entry, focus = true) {
  state.active = entry;
  const { result, input, title } = entry;
  const copy = decisionCopy[result.decision];
  $("#result-panel").className = `result-panel has-result ${result.decision}`;
  $("#result-state").textContent = "CHECK COMPLETE";
  const icon =
    result.decision === "approve"
      ? '<path d="m5 12 4 4L19 6"/>'
      : '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16h.01"/>';
  $("#result-content").innerHTML =
    `<h3 id="result-title" tabindex="-1">${escapeHTML(copy.title)}</h3><p class="result-subtitle">${escapeHTML(copy.description)}</p><p class="model-estimate">Model risk estimate <strong>${percent(result.probability)}</strong></p><h4 class="receipt-section-title">What stood out</h4>${renderFindings(result)}${result.model_decision !== "approve" ? '<div class="finding">' + svg(icon) + "<div><strong>The model crossed a decision threshold</strong><p>Learned transaction patterns also suggest review. This is an estimate, not proof that the transaction is fraudulent.</p></div></div>" : ""}<div class="next-step"><h4>Your next step</h4><p>${escapeHTML(copy.next)}</p></div><details class="receipt-details"><summary>How to read this result ${svg('<path d="m6 9 6 6 6-6"/>')}</summary><p class="field-help">The trained model suggests an action using probability thresholds. Contextual checks can make that action more cautious without changing the probability. The most cautious outcome is shown above.</p><dl><div><dt>Model suggestion</dt><dd>${escapeHTML(decisionCopy[result.model_decision].label)}</dd></div><div><dt>Model thresholds</dt><dd>Review from ${percent(result.thresholds.review)} · Pause from ${percent(result.thresholds.block)}</dd></div><div><dt>Model version</dt><dd>${escapeHTML(result.model_version)} · ${escapeHTML(result.data_source)}</dd></div><div><dt>Check reference</dt><dd>${escapeHTML(result.prediction_id)}</dd></div></dl></details><button type="button" class="button button-secondary download-button" id="download-summary">Save this summary ${svg('<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>')}</button><p class="receipt-input">${escapeHTML(title)} · ${money(input.amount)}<br>Synthetic example · No real payment was processed</p>`;
  $("#download-summary").addEventListener("click", downloadSummary);
  $("#result-announcement").textContent =
    `${copy.label}. Model risk estimate ${percent(result.probability)}. ${result.signals.length} contextual warnings. A suggested next step is available.`;
  if (focus) $("#result-title").focus({ preventScroll: false });
}

function downloadSummary() {
  if (!state.active) return;
  const { result, input, title } = state.active;
  const copy = decisionCopy[result.decision];
  const lines = [
    "FRAUDLINE / EXAMPLE CHECK SUMMARY",
    "",
    "Synthetic educational example. No real payment was processed.",
    `Example: ${title}`,
    `Amount: ${money(input.amount)}`,
    `Suggested outcome: ${copy.label}`,
    `Model risk estimate: ${percent(result.probability)}`,
    "",
    "WHAT STOOD OUT",
    ...result.signals.map((item) => `${item.title}: ${item.evidence}`),
    ...(result.signals.length
      ? []
      : ["No additional contextual warning signals."]),
    "",
    "NEXT STEP",
    copy.next,
    "",
    `Model: ${result.model_version}`,
    `Reference: ${result.prediction_id}`,
    "",
    "A model estimate and contextual checks are separate signals, not proof of fraud. Public records are temporary.",
  ];
  const url = URL.createObjectURL(
    new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `fraudline-example-${result.prediction_id.slice(0, 8)}.txt`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderRecent() {
  $("#recent-section").hidden = !state.recent.length;
  $("#recent-list").innerHTML = state.recent
    .map(
      (entry, index) =>
        `<button class="recent-button" type="button" data-recent="${index}"><strong>${escapeHTML(entry.title)}</strong><span>${money(entry.input.amount)}<span class="decision-word ${entry.result.decision}">${escapeHTML(decisionCopy[entry.result.decision].label)}</span></span></button>`,
    )
    .join("");
  document.querySelectorAll("[data-recent]").forEach((button) =>
    button.addEventListener("click", () => {
      if (state.busy) return;
      const entry = state.recent[Number(button.dataset.recent)];
      selectExample(entry.caseId);
      fillDetails(entry.input);
      renderResult(entry);
    }),
  );
}

$("#all-examples").addEventListener("change", (event) =>
  selectExample(event.target.value),
);
$("#client-form").addEventListener("input", () => {
  if (state.active) resetResult();
  $("#score-error").hidden = true;
  $("#amount-error").hidden = true;
  $("#client-amount").removeAttribute("aria-invalid");
});
$("#client-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy || !state.selected) return;
  const amount = Number($("#client-amount").value);
  if (!Number.isFinite(amount) || amount <= 0 || amount > 1000000) {
    $("#amount-error").textContent =
      "Enter an example amount between $0.01 and $1,000,000.";
    $("#amount-error").hidden = false;
    $("#client-amount").setAttribute("aria-invalid", "true");
    $("#client-amount").focus();
    return;
  }
  const input = structuredClone(state.selected.transaction);
  input.amount = amount;
  input.device_type = $("#client-device").value;
  input.context.merchant_category = $("#client-merchant").value;
  input.context.new_payee = $("#client-payee").checked;
  input.context.withdrawal = $("#client-payee").checked;
  input.context.password_changed_minutes = $("#client-password").checked
    ? 5
    : null;
  input.transaction_id = `CLIENT-${Date.now()}`;
  const selected = state.selected;
  setBusy(true);
  $("#score-error").hidden = true;
  $("#result-state").textContent = "CHECKING THE EXAMPLE";
  $("#result-content").innerHTML =
    `<div class="loading-result"><div>${svg('<path d="M3 12h4l3-7 5 14 3-7h3"/>')}<p>Looking at the signals.</p><small>Comparing this example with its earlier activity…</small></div></div>`;
  $("#result-announcement").textContent = "Checking this example. Please wait.";
  try {
    const result = await api("/predict", input);
    if (
      !decisionCopy[result.decision] ||
      !decisionCopy[result.model_decision] ||
      !Number.isFinite(result.probability) ||
      !Array.isArray(result.signals)
    )
      throw new Error(
        "The service returned an incomplete result. Please try again.",
      );
    const entry = { caseId: selected.id, title: selected.title, input, result };
    state.recent.unshift(entry);
    state.recent = state.recent.slice(0, 3);
    renderRecent();
    renderResult(entry);
  } catch (error) {
    resetResult();
    $("#score-error").textContent =
      error.name === "TimeoutError"
        ? "This check took too long. The service may be waking up. Please try again."
        : error.message;
    $("#score-error").hidden = false;
    $("#result-announcement").textContent =
      "The example could not be checked. No result is available.";
  } finally {
    setBusy(false);
  }
});

async function initialize() {
  $("#connection-error").hidden = true;
  $("#retry").disabled = true;
  try {
    const [examples] = await Promise.all([
      api("/api/scenarios"),
      api("/ready"),
    ]);
    state.cases = examples.scenarios;
    if (!Array.isArray(state.cases) || !state.cases.length)
      throw new Error("The example library is unavailable. Please try again.");
    $("#examples").innerHTML = Object.entries(exampleLabels)
      .filter(([id]) => state.cases.some((item) => item.id === id))
      .map(
        ([id, label]) =>
          `<button class="example-button" type="button" data-example="${id}" aria-pressed="false">${svg(icons[id])}<span>${label}</span></button>`,
      )
      .join("");
    document
      .querySelectorAll("[data-example]")
      .forEach((button) =>
        button.addEventListener("click", () =>
          selectExample(button.dataset.example),
        ),
      );
    $("#all-examples").innerHTML = state.cases
      .map(
        (item) =>
          `<option value="${escapeHTML(item.id)}">${escapeHTML(item.title)}</option>`,
      )
      .join("");
    setBusy(false);
    selectExample("normal");
  } catch (error) {
    $("#connection-error-text").textContent =
      "We couldn't connect to the example-checking service. You can still read how it works below. Try again when you're ready.";
    $("#connection-error").hidden = false;
    $("#example-fieldset").disabled = true;
    $("#details-fieldset").disabled = true;
    $("#all-examples").disabled = true;
  } finally {
    $("#retry").disabled = false;
  }
}
$("#retry").addEventListener("click", initialize);
initialize();

const menuToggle = $("#menu-toggle");
function closeNavigation() {
  $(".site-header").classList.remove("nav-open");
  menuToggle.setAttribute("aria-expanded", "false");
  menuToggle.setAttribute("aria-label", "Open navigation");
}
menuToggle.addEventListener("click", () => {
  const open = menuToggle.getAttribute("aria-expanded") !== "true";
  $(".site-header").classList.toggle("nav-open", open);
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
});
$("#client-navigation").addEventListener("click", (event) => {
  if (event.target.closest("a")) closeNavigation();
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    menuToggle.getAttribute("aria-expanded") === "true"
  ) {
    closeNavigation();
    menuToggle.focus();
  }
});
