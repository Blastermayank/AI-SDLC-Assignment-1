// Evaluation dashboard (FR-030 to FR-033; task T040). Read-only views of saved reports.
import { get } from './api.js';
import { badge, clear, el, formatPercent, formatTimestamp, resultBadge, statusBadge } from './dom.js';
import { registerSection } from './registry.js';

const $ = (id) => document.getElementById(id);
let historyData = null;

const fileName = (path) => String(path).split('/').pop();

function runLabel(run) {
  const name = fileName(run.file);
  const match = name.match(/^eval-results-run-(\d+)-/);
  const score = typeof run.aggregate_score === 'number' ? formatPercent(run.aggregate_score) : 'no final score';
  const label = match ? `Run ${match[1]}` : 'Current report';
  return `${label} · ${run.status} · ${score}`;
}

function tile(label, value) {
  return el('div', { className: 'tile' }, [
    el('div', { className: 'tile-label', text: label }),
    el('div', { className: 'tile-value' }, value),
  ]);
}

function renderSummary(data) {
  const report = data.report;
  const score = typeof report.aggregate_score === 'number'
    ? formatPercent(report.aggregate_score)
    : (typeof report.partial_score === 'number' ? `partial ${formatPercent(report.partial_score)}` : 'none');
  clear($('ev-summary')).append(
    tile('Status', statusBadge(report.status)),
    tile('Score', score),
    tile('Threshold', formatPercent(report.threshold, 0)),
    tile('Completed', `${report.completed_cases} / ${report.total_cases}`),
    tile('Passed', String(report.passed_cases)),
    tile('Model', el('span', { className: 'mono small', text: report.model })),
  );
  const details = [`Source: ${data.source}`, `Run time: ${formatTimestamp(report.timestamp_utc)}`];
  if (report.dataset_sha256) details.push(`Dataset fingerprint: ${report.dataset_sha256.slice(0, 16)}…`);
  if (report.service_error) {
    details.push(`Stopped by ${report.service_error.error_type} on case ${report.service_error.case_id} (service error, not an application failure)`);
  }
  $('ev-source').textContent = details.join(' · ');
}

function layerCell(result, layer, interrupted) {
  if (interrupted) return el('td', {}, badge('not run', 'neutral'));
  return el('td', {}, result[layer] ? badge('PASS', 'pass') : badge('FAIL', 'fail'));
}

function detailRow(result, testCase) {
  const body = el('div', { className: 'stack-sm' });
  if (testCase) {
    body.append(
      el('div', {}, [el('strong', { text: 'Input' }), el('pre', { text: testCase.input === '' ? '(empty)' : testCase.input })]),
      el('div', { className: 'small', text: `Expected category: ${testCase.expected_vuln} · expected status: ${testCase.expected_status}` }),
    );
  }
  body.append(
    el('div', {}, [el('strong', { text: 'Explanation' }), el('div', { className: 'small', text: result.error || 'All layers passed.' })]),
    el('div', {}, [el('strong', { text: 'Model output' }), el('pre', { text: result.model_output ? JSON.stringify(result.model_output, null, 2) : '(no output)' })]),
  );
  const row = el('tr', { className: 'case-detail' }, el('td', { attrs: { colspan: 7 } }, body));
  row.hidden = true;
  return row;
}

function renderCases(data) {
  const tbody = clear($('ev-cases'));
  const cases = new Map((data.cases ?? []).map((testCase) => [testCase.id, testCase]));
  const results = data.report.results ?? [];
  if (results.length === 0) {
    tbody.append(el('tr', { className: 'empty-row' }, el('td', { text: 'No case results in this report.', attrs: { colspan: 7 } })));
  }
  for (const result of results) {
    const interrupted = Boolean(result.service_error || result.execution_error);
    const testCase = cases.get(result.id);
    const detail = detailRow(result, testCase);
    const button = el('button', { className: 'btn btn-secondary btn-small', text: 'Details', attrs: { type: 'button', 'aria-expanded': 'false' } });
    button.addEventListener('click', () => {
      detail.hidden = !detail.hidden;
      button.setAttribute('aria-expanded', String(!detail.hidden));
    });
    let className = 'case-row';
    if (interrupted) className += ' is-interrupted';
    else if (!result.pass) className += ' is-failed';
    tbody.append(
      el('tr', { className }, [
        el('td', { text: result.id }),
        el('td', { text: testCase?.type ?? '-' }),
        layerCell(result, 'layer1', interrupted),
        layerCell(result, 'layer2', interrupted),
        layerCell(result, 'layer3', interrupted),
        el('td', {}, interrupted ? badge('INTERRUPTED', 'warn') : resultBadge(result.pass)),
        el('td', {}, button),
      ]),
      detail,
    );
  }
  const note = $('ev-cases-note');
  note.textContent = data.cases_note ?? '';
  note.hidden = !data.cases_note;
}

function renderLatestNotice(currentReport) {
  const notice = $('ev-latest');
  const latest = historyData?.latest_completed;
  if (currentReport?.status === 'INCOMPLETE' && latest) {
    notice.textContent = `The current report is INCOMPLETE because a Gemini service error stopped the run. The latest completed run is ${runLabel(latest)} (${formatTimestamp(latest.timestamp_utc)}). Use "View latest completed run" to see it.`;
    notice.hidden = false;
  } else {
    notice.hidden = true;
  }
}

async function showReport(name) {
  const query = name && name !== 'eval-results.json' ? `?report=${encodeURIComponent(name)}` : '';
  const result = await get(`/api/part-1b/evaluation${query}`);
  if (!result.ok || !result.data) {
    clear($('ev-summary')).append(el('div', { className: 'callout callout-warn', text: result.data?.error?.message ?? 'Report unavailable.' }));
    clear($('ev-cases'));
    return;
  }
  $('ev-report-select').value = result.data.file;
  renderSummary(result.data);
  renderCases(result.data);
  if (result.data.is_current) renderLatestNotice(result.data.report);
  else $('ev-latest').hidden = true;
}

function renderHistory() {
  const holder = clear($('ev-history'));
  const runs = historyData?.runs ?? [];
  holder.append(el('div', { className: 'callout callout-warn', text: historyData?.caveat ?? '' }));
  const rows = runs.map((run) => {
    const view = el('button', { className: 'btn btn-secondary btn-small', text: 'View', attrs: { type: 'button' } });
    view.addEventListener('click', () => {
      showReport(fileName(run.file));
      $('ev-summary').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    const score = typeof run.aggregate_score === 'number'
      ? formatPercent(run.aggregate_score)
      : (typeof run.partial_score === 'number' ? `partial ${formatPercent(run.partial_score)}` : '-');
    return el('tr', { className: 'history-run' }, [
      el('td', {}, [el('span', { className: 'mono small', text: fileName(run.file) }), run.is_current ? el('div', {}, badge('current', 'info')) : null]),
      el('td', { className: 'nowrap', text: formatTimestamp(run.timestamp_utc) }),
      el('td', { className: 'num', text: run.completed_cases !== undefined ? `${run.completed_cases} / ${run.total_cases}` : '-' }),
      el('td', { className: 'num', text: run.passed_cases ?? '-' }),
      el('td', { className: 'num', text: score }),
      el('td', {}, statusBadge(run.status)),
      el('td', { text: (run.failed_case_ids ?? []).join(', ') || '-' }),
      el('td', { text: (run.interrupted_case_ids ?? []).join(', ') || '-' }),
      el('td', {}, run.status === 'UNREADABLE' ? null : view),
    ]);
  });
  holder.append(
    el('div', { className: 'table-wrap section-block' }, el('table', {}, [
      el('thead', {}, el('tr', {}, ['Report', 'Run time', 'Completed', 'Passed', 'Score', 'Status', 'Failed cases', 'Interrupted', ''].map((title, index) =>
        el('th', { className: [2, 3, 4].includes(index) ? 'num' : '', text: title })))),
      el('tbody', {}, rows),
    ])),
  );

  const select = clear($('ev-report-select'));
  for (const run of [...runs].reverse()) {
    if (run.status === 'UNREADABLE') continue;
    select.append(el('option', { text: runLabel(run), attrs: { value: fileName(run.file) } }));
  }
}

async function init() {
  const history = await get('/api/part-1b/evaluation/history');
  historyData = history.ok ? history.data : { runs: [], caveat: '', latest_completed: null };
  renderHistory();
  $('ev-report-select').addEventListener('change', (event) => showReport(event.target.value));
  $('ev-view-latest').addEventListener('click', () => {
    if (historyData.latest_completed) showReport(fileName(historyData.latest_completed.file));
  });
  $('ev-view-latest').disabled = !historyData.latest_completed;
  await showReport('eval-results.json');
}

registerSection('evaluation', init);
