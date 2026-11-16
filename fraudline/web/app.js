const $ = selector => document.querySelector(selector);
const state = { samples: [], rows: [], cursor: 0, selected: null, playing: false, timer: null, busy: false, model: null, drift: null };
const money = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(value);
const percent = value => `${(value * 100).toFixed(1)}%`;
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {log_amount:'Transaction amount', hour_sin:'Time of day (sin)', hour_cos:'Time of day (cos)', product:'Product category', network:'Card network', card_type:'Card type', log_distance:'Transaction distance', distance_missing:'Distance missing', identity_present:'Identity available'};

async function api(path, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, {signal: controller.signal, ...(body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {})});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'The request was rejected. Check the input values.');
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The scoring service timed out. It may be waking up; try again shortly.');
    throw error;
  } finally { clearTimeout(timeout); }
}
function notice(message) { $('#notice').textContent = message; $('#notice').hidden = !message; }
function show(view) {
  if (view !== 'desk') pause();
  document.querySelectorAll('.view').forEach(section => section.hidden = section.id !== view);
  document.querySelectorAll('[data-view]').forEach(button => { if (button.dataset.view === view) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); });
  if (view === 'monitoring') refreshMonitoring();
}
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => show(button.dataset.view)));
$('#lineage-link').addEventListener('click', event => {event.preventDefault(); show('models');});

function renderLedger() {
  $('#ledger-count').textContent = String(state.rows.length).padStart(2,'0');
  $('#transactions').innerHTML = [...state.rows].reverse().map(row => {
    const time = row.input.time_offset;
    const day = Math.floor(time / 86400) + 1;
    const clock = `${String(Math.floor(time / 3600) % 24).padStart(2,'0')}:${String(Math.floor(time / 60) % 60).padStart(2,'0')}`;
    return `<tr class="${row.result.prediction_id === state.selected ? 'selected' : ''}"><td><button class="transaction-select" data-id="${escape(row.result.prediction_id)}" aria-label="Inspect ${escape(row.input.transaction_id)}" aria-pressed="${row.result.prediction_id === state.selected}"><strong>${escape(row.input.transaction_id)}</strong><span>Day ${day}, ${clock} / ${escape(row.input.network)}</span></button></td><td>${money(row.input.amount)}</td><td class="risk-number">${percent(row.result.probability)}</td><td><span class="status ${row.result.decision}">${escape(row.result.decision)}</span></td><td><svg class="row-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h10M9 4l4 4-4 4"/></svg></td></tr>`;
  }).join('');
  document.querySelectorAll('[data-id]').forEach(button => button.addEventListener('click', () => {state.selected = button.dataset.id; renderLedger(); renderReceipt();}));
}
function renderReceipt() {
  const row = state.rows.find(item => item.result.prediction_id === state.selected);
  if (!row) return;
  const {input, result} = row;
  $('#receipt-number').textContent = input.transaction_id;
  const max = Math.max(...result.reasons.map(reason => Math.abs(reason.contribution)), .001);
  const t = result.thresholds;
  $('#receipt-content').innerHTML = `<div class="receipt-heading"><h2>${result.decision === 'approve' ? 'Approve' : result.decision === 'review' ? 'Manual review' : 'Block'}</h2><span class="receipt-amount">${money(input.amount)}</span></div><div class="score">${(result.probability * 100).toFixed(1)}<small>%</small></div><p class="score-caption">Estimated fraud probability / ${escape(result.data_source)} model</p><div class="threshold-track"><span class="review-zone"></span><span class="block-zone"></span><span class="score-marker"></span></div><div class="threshold-labels"><span>0%</span><span>Review ${percent(t.review)}</span><span>Block ${percent(t.block)}</span><span>100%</span></div><h3>What influenced this score</h3>${result.reasons.map(reason => `<div class="reason"><div class="reason-label"><span>${escape(reason.label)}</span><span>${reason.contribution > 0 ? '+' : ''}${reason.contribution.toFixed(3)}</span></div><div class="reason-bar"><i class="${reason.direction}" data-value="${Math.abs(reason.contribution) / max * 100}"></i></div></div>`).join('')}<div class="receipt-facts"><div><span>Contribution scale</span><strong>Raw model log-odds</strong></div><div><span>Model version</span><strong>${escape(result.model_version)}</strong></div><div><span>Audit reference</span><strong>${escape(result.prediction_id.slice(0,18))}</strong></div><div><span>Data provenance</span><strong>${input.transaction_id.startsWith('SYN') ? 'Synthetic replay' : 'Manual test input'}</strong></div></div>`;
  $('.review-zone').style.left = `${t.review * 100}%`; $('.review-zone').style.width = `${(t.block-t.review) * 100}%`;
  $('.block-zone').style.left = `${t.block * 100}%`; $('.block-zone').style.width = `${(1-t.block) * 100}%`;
  $('.score-marker').style.left = `${Math.min(99.7,result.probability * 100)}%`;
  document.querySelectorAll('[data-value]').forEach(bar => bar.style.width = `${bar.dataset.value}%`);
}
function addRow(input, result) {
  state.rows.push({input,result});
  if (state.rows.length > 100) state.rows.shift();
  state.selected = result.prediction_id;
  renderLedger(); renderReceipt();
}
function pause() { state.playing = false; clearTimeout(state.timer); $('#play span').textContent = 'Play replay'; }
async function next() {
  if (state.busy) return;
  if (state.cursor >= state.samples.length) {pause(); notice('Replay complete. Reload the page to start a fresh synthetic replay.'); return;}
  state.busy = true; $('#step').disabled = true;
  const input = state.samples[state.cursor];
  const start = performance.now();
  try {
    const result = await api('/predict', input); state.cursor++; addRow(input,result);
    $('#observed').textContent = `${Math.round(performance.now()-start)} ms last request, including network`;
    notice('');
  } catch (error) {pause(); notice(error.message);}
  finally {state.busy = false; $('#step').disabled = false;}
  if (state.playing) state.timer = setTimeout(next, Number($('#speed').value));
}
$('#step').addEventListener('click', () => {pause(); next();});
$('#play').addEventListener('click', () => { if (state.playing) pause(); else {state.playing = true; $('#play span').textContent = 'Pause replay'; next();} });
document.addEventListener('visibilitychange', () => {if (document.hidden) pause();});
$('#score-form').addEventListener('submit', async event => {
  event.preventDefault(); pause(); const button = event.target.querySelector('button'); button.disabled = true;
  const form = new FormData(event.target); $('#form-error').textContent = '';
  const input = {transaction_id:`TEST-${Date.now()}`, amount:Number(form.get('amount')), time_offset:Number(form.get('hour')) * 3600,
    distance:form.get('distance') === '' ? null : Number(form.get('distance')), product:form.get('product'), network:form.get('network'), card_type:form.get('card_type'), identity_present:form.has('identity')};
  try { addRow(input, await api('/predict',input)); } catch (error) {$('#form-error').textContent = error.message;}
  finally {button.disabled = false;}
});
function renderModels() {
  const {metadata:m, evaluation:e, registry:r} = state.model;
  const rows = [['PR-AUC', 'pr_auc'], ['ROC-AUC','roc_auc'], ['Brier score','brier'], ['Recall at review threshold','recall'], ['False-positive rate','false_positive_rate'], ['Hypothetical cost / transaction','cost_per_transaction']];
  $('#model-content').innerHTML = `<div><h3>Final chronological test interval</h3><table class="metrics-table"><thead><tr><th>Measure</th><th>Logistic baseline</th><th>LightGBM</th></tr></thead><tbody>${rows.map(([label,key]) => `<tr><td>${label}</td><td>${e.baseline[key].toFixed(4)}</td><td>${e.final_test[key].toFixed(4)}</td></tr>`).join('')}</tbody></table><p class="footnote">${escape(e.warning)}. Cost figures use hypothetical review and false-block costs; they are not measured financial savings.</p><h3>Registry history</h3><table class="metrics-table"><thead><tr><th>Version</th><th>Outcome</th></tr></thead><tbody>${r.history.slice(-8).map(item => `<tr><td>${escape(item.version)}</td><td>${item.action === 'rollback' ? 'Rolled back' : item.promoted ? 'Promoted' : 'Candidate retained'}</td></tr>`).join('')}</tbody></table></div><div><h3>Reproducibility record</h3><dl class="fact-list"><div><dt>Data source</dt><dd>${escape(m.data_source)} / ${m.rows.toLocaleString()} transactions</dd></div><div><dt>Training version</dt><dd>${escape(m.version)}</dd></div><div><dt>Data SHA-256</dt><dd>${escape(m.data_sha256)}</dd></div><div><dt>Chronological split</dt><dd>${Object.entries(m.splits).map(([name,s]) => `${escape(name)}: ${s.rows.toLocaleString()} rows`).join('<br>')}</dd></div><div><dt>Production bundle</dt><dd>Pinned at process startup; verified model hash</dd></div></dl></div>`;
}
function renderDrift(name) {
  const report = state.drift?.[name]; if (!report) return;
  document.querySelectorAll('[data-scenario]').forEach(button => {const active = button.dataset.scenario === name; button.className = active ? 'primary' : 'secondary'; button.setAttribute('aria-pressed',String(active));});
  $('#drift-content').innerHTML = `<div><p class="footnote">${escape(report.provenance)}</p><h3 class="drift-status ${report.drifted ? 'alert' : ''}">${report.drifted ? 'A different<br>distribution.' : 'Within the<br>reference pattern.'}</h3><dl class="fact-list"><div><dt>Sample size</dt><dd>${report.samples.toLocaleString()} synthetic transactions</dd></div><div><dt>Mean predicted probability</dt><dd>${percent(report.prediction_mean)}</dd></div><div><dt>Retraining status</dt><dd>${escape(report.retraining)}</dd></div></dl></div><div><h3>Feature distribution distance</h3>${report.features.map(item => `<div class="drift-feature"><span>${escape(labels[item.feature] || item.feature)}</span><div class="drift-bar"><span data-distance="${item.distance}"></span></div><span>${item.distance.toFixed(3)}</span></div>`).join('')}<p class="footnote">Jensen–Shannon distance. Values above 0.20 raise the drift flag. Data drift is not proof of reduced accuracy.</p></div>`;
  document.querySelectorAll('[data-distance]').forEach(bar => bar.style.width = `${Math.min(100, Number(bar.dataset.distance) * 100)}%`);
}
document.querySelectorAll('[data-scenario]').forEach(button => button.addEventListener('click', () => renderDrift(button.dataset.scenario)));
async function refreshMonitoring() {
  try {const report = await api('/api/monitoring'); $('#monitoring-content').innerHTML = `<h3>${report.status === 'ready' ? (report.drifted ? 'Drift alert raised' : 'No drift alert') : report.status === 'not_run' ? 'No scheduled report yet' : 'Waiting for enough samples'}</h3><dl class="fact-list"><div><dt>Recorded monitoring samples</dt><dd>${report.samples || 0}</dd></div><div><dt>Generated at</dt><dd>${escape(report.generated_at || 'Not run')}</dd></div><div><dt>Retraining</dt><dd>${escape(typeof report.retraining === 'string' ? report.retraining : 'See local lifecycle report')}</dd></div><div><dt>Ground-truth performance</dt><dd>${report.performance?.status === 'ready' ? `PR-AUC ${report.performance.pr_auc.toFixed(4)} across ${report.performance.labeled_rows} labeled decisions` : 'Insufficient delayed labels; accuracy is not inferred from drift'}</dd></div></dl>`;} catch (error) {$('#monitoring-content').textContent = error.message;}
}
$('#refresh-monitoring').addEventListener('click',refreshMonitoring);
async function init() {
  $('#play').disabled = true; $('#step').disabled = true;
  try {
    const ready = await api('/ready'); $('#model-version').textContent = ready.model_version;
    $('#model-source').textContent = `${ready.data_source} training / verified bundle`; $('#connection').textContent = 'Scoring service connected';
    const [sampleData, model] = await Promise.all([api('/api/samples'),api('/api/model')]);
    state.samples = sampleData.transactions; state.model = model; renderModels();
    const start = performance.now();
    const inputs = state.samples.slice(0,10);
    const batch = await api('/predict/batch',{transactions:inputs});
    state.rows = batch.predictions.map((result,index) => ({input:inputs[index],result}));
    state.cursor = inputs.length; state.selected = state.rows.at(-1).result.prediction_id;
    renderLedger(); renderReceipt(); $('#observed').textContent = `${Math.round(performance.now()-start)} ms initial batch, including network`;
    $('#play').disabled = false; $('#step').disabled = false;
    try {state.drift = await api('/api/drift'); renderDrift('reference');} catch(error) {$('#drift-content').textContent = error.message;}
  } catch (error) { notice(error.message); $('#connection').textContent = 'Scoring service unavailable'; $('#model-version').textContent = 'Unavailable'; $('#model-source').textContent = 'Reload after the service is ready'; $('#transactions').innerHTML = '<tr><td colspan="5" class="empty">The scoring service is unavailable. No sample scores have been substituted.</td></tr>'; }
}
init();
