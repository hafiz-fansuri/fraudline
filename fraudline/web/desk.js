const $ = (s) => document.querySelector(s);
const esc = (v) =>
  String(v).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (v) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    v,
  );
const labels = {
  approve: "No alert",
  review: "Review suggested",
  block: "Pause suggested",
  unchecked: "Not checked",
};
const state = {
  rows: [],
  selected: null,
  results: new Map(),
  busy: false,
  revision: 0,
};
function error(message = "") {
  $("#error").textContent = message;
  $("#error").hidden = !message;
}
async function api(url, body) {
  const response = await fetch(
    url,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {},
  );
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 422)
      throw new Error(
        "The transaction does not match the input contract. Check field names, required fields, types and allowed values in the example JSON or API reference.",
      );
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : "The service could not complete the request. Try again.",
    );
  }
  return result;
}
function download(name, value) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderQueue() {
  const query = $("#search").value.toLowerCase(),
    filter = $("#filter").value;
  const rows = state.rows.filter(
    (row) =>
      `${row.transaction.transaction_id} ${row.title}`
        .toLowerCase()
        .includes(query) &&
      (filter === "all" ||
        (state.results.get(row.transaction.transaction_id)?.risk.decision ||
          "unchecked") === filter),
  );
  $("#queue").innerHTML = rows.length
    ? rows
        .map((row) => {
          const id = row.transaction.transaction_id,
            status = state.results.get(id)?.risk.decision || "unchecked";
          return `<button type="button" class="transaction" data-id="${esc(id)}" aria-pressed="${state.selected === id}"><strong>${esc(row.title)}</strong><small>${esc(id)}</small><span class="row"><span class="amount">${money(row.transaction.amount)}</span><span class="tag ${status}">${labels[status]}</span></span></button>`;
        })
        .join("")
    : "<p>No transactions match. Clear the search or change the status filter.</p>";
  $("#queue-note").textContent =
    `${state.rows.length} transactions · ${state.rows[0]?.provenance || "Imported synthetic data"} · USD`;
}
function renderEvidence(investigation) {
  if (investigation.status === "abstained")
    return `<p>${esc(investigation.answer)}</p>`;
  return `<p class="evidence-note">${esc(investigation.mode)}. Illustrative guidance; not bank-approved policy.</p><h4>Suggested human review steps</h4><ol class="steps">${investigation.next_steps.map((step) => `<li>${esc(step.text)} <a href="#evidence-${step.citation}">[${step.citation}]</a></li>`).join("")}</ol><details><summary>Read the cited guidance</summary>${investigation.answer
    .split("\n\n")
    .map((p) => `<p>${esc(p)}</p>`)
    .join(
      "",
    )}</details><h4>Source passages</h4>${investigation.evidence.map((source, i) => `<details class="evidence" id="evidence-${i + 1}"><summary>[${i + 1}] ${esc(source.title)}</summary><p>${esc(source.content)}</p><small>${esc(source.publisher)} · ${esc(source.version)}</small><small>SHA-256: ${esc(source.sha256)}</small><a href="${esc(source.url)}">Open playbook</a></details>`).join("")}<details class="trace"><summary>Investigation steps and checks</summary><ol>${investigation.plan.map((step) => `<li>${esc(step.tool.replaceAll("_", " "))} — ${esc(step.status)}</li>`).join("")}</ol><p>Citation IDs ${investigation.citations_valid ? "validated" : "unverified"}. This checks references, not whether a claim is true.</p></details>`;
}
function renderReceipt(row, result) {
  const t = row.transaction,
    r = result.risk;
  $("#receipt").innerHTML =
    `<div class="receipt-top"><div><h3 id="case-title">${esc(row.title)}</h3><span class="case-id">${esc(t.transaction_id)}</span></div><button id="export" type="button">Save review</button></div><div class="assessment"><span class="tag ${r.decision}">${labels[r.decision]}</span><div class="probability">${(r.probability * 100).toFixed(2)}%</div><p>Calibrated model estimate · not a confirmed fraud rate</p><p>Model suggests: ${labels[r.model_decision]}. Context controls may escalate the review.</p><div class="facts"><span>${money(t.amount)} USD</span><span>${t.history?.length || 0} earlier events supplied</span><span>Device: ${esc(t.device_type || "unknown")}</span></div></div><h4>What needs attention</h4>${r.signals.length ? r.signals.map((s) => `<div class="signal"><strong>${esc(s.title)}</strong><p>${esc(s.evidence)}</p></div>`).join("") : '<p class="evidence-note">No contextual control fired. Missing inputs and an absence of alerts do not establish that a payment is safe.</p>'}<details><summary>Model details and limitations</summary><p class="evidence-note">Version ${esc(r.model_version)} · ${esc(r.data_source)}. Review threshold ${(r.thresholds.review * 100).toFixed(2)}%; pause threshold ${(r.thresholds.block * 100).toFixed(2)}%.</p><p class="evidence-note">${esc(r.reason_scale)}</p><ul class="steps">${r.reasons.map((reason) => `<li>${esc(reason.label)}: ${esc(reason.direction)} LightGBM-stage score</li>`).join("")}</ul><p class="evidence-note">Audit reference: ${esc(r.prediction_id)}. Public deployment storage is temporary.</p></details><section class="investigation"><h3>Investigate with evidence</h3><form id="ask-form"><div><label for="question">Question about the selected transaction</label><textarea id="question" minlength="8" maxlength="1200" required>What evidence and human review steps apply to this transaction?</textarea></div><button class="primary" type="submit">Find guidance</button></form><div id="evidence" aria-live="polite">${renderEvidence(result.investigation)}</div></section>`;
  $("#export").onclick = () =>
    download(`${t.transaction_id}-review.json`, {
      provenance: row.provenance,
      transaction_id: t.transaction_id,
      ...result,
    });
  $("#ask-form").onsubmit = async (event) => {
    event.preventDefault();
    await select(t.transaction_id, $("#question").value);
  };
}
async function select(id, question) {
  if (state.busy) return;
  const row = state.rows.find((item) => item.transaction.transaction_id === id);
  if (!row) return;
  state.selected = id;
  renderQueue();
  error();
  if (state.results.has(id) && !question) {
    renderReceipt(row, state.results.get(id));
    return;
  }
  state.busy = true;
  const revision = state.revision;
  $("#receipt").setAttribute("aria-busy", "true");
  $("#receipt").innerHTML =
    '<div class="empty" role="status"><h3>Reviewing the transaction…</h3><p>Scoring its inputs and finding relevant playbooks.</p></div>';
  try {
    const result = await api("/api/review", {
      transaction: row.transaction,
      ...(question ? { question } : {}),
    });
    if (revision !== state.revision) return;
    state.results.set(id, result);
    renderReceipt(row, result);
    if (question) $("#question").value = question;
  } catch (e) {
    error(e.message);
    $("#receipt").innerHTML =
      '<div class="empty"><h3>Review unavailable</h3><p>Select this transaction again to retry. No score has been substituted.</p></div>';
  } finally {
    state.busy = false;
    $("#receipt").removeAttribute("aria-busy");
    renderQueue();
  }
}
$("#queue").onclick = (e) => {
  const button = e.target.closest("[data-id]");
  if (button) select(button.dataset.id);
};
$("#search").oninput = renderQueue;
$("#filter").onchange = renderQueue;
$("#template").onclick = () =>
  download("fraudline-synthetic-transactions.json", {
    transactions: state.rows.map((row) => row.transaction),
  });
$("#import-button").onclick = () => $("#upload").click();
$("#import-button").onclick = () => $("#upload").click();
$("#upload").onchange = async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  if (state.busy) {
    error("Wait for the current review to finish, then import the file again.");
    return;
  }
  try {
    error();
    if (file.size > 256 * 1024)
      throw new Error("Use a JSON file smaller than 256 KiB.");
    const data = JSON.parse(await file.text());
    if (
      !Array.isArray(data.transactions) ||
      !data.transactions.length ||
      data.transactions.length > 100
    )
      throw new Error(
        "Provide a transactions list containing 1–100 synthetic transactions.",
      );
    const ids = data.transactions.map((t) => t.transaction_id);
    if (
      ids.some((id) => typeof id !== "string") ||
      new Set(ids).size !== ids.length
    )
      throw new Error("Every transaction needs a unique transaction_id.");
    // Validate all rows together before changing the queue. The API owns the contract.
    state.busy = true;
    $("#queue-note").textContent = "Validating imported transactions…";
    await api("/predict/batch", data);
    state.revision++;
    state.results.clear();
    state.selected = null;
    state.rows = data.transactions.map((t) => ({
      title: t.transaction_id,
      transaction: t,
      provenance: "Imported synthetic data",
    }));
    renderQueue();
    $("#receipt").innerHTML =
      '<div class="empty"><h3>Import ready</h3><p>Select a transaction to review its findings.</p></div>';
  } catch (e) {
    error(
      e instanceof SyntaxError
        ? "The file is not valid JSON. Download the example and keep its structure."
        : e.message,
    );
  } finally {
    state.busy = false;
    renderQueue();
  }
};
async function init() {
  try {
    const data = await api("/api/scenarios");
    state.rows = data.scenarios;
    renderQueue();
    await select(state.rows[0].transaction.transaction_id);
  } catch (e) {
    error(e.message);
    $("#queue-note").textContent =
      "Examples unavailable. Reload the page to retry.";
  }
}
init();
