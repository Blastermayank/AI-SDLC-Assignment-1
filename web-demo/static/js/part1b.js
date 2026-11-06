// Part 1B live code review (FR-020 to FR-028; task T034). Findings come only from the server's
// response to a live Gemini call and are rendered as text (Constitution IV and V).
import { post } from './api.js';
import { badge, clear, el } from './dom.js';
import { registerSection } from './registry.js';

const MAX_CHARS = 20000;

const SAMPLES = {
  sql: [
    'import sqlite3',
    '',
    'def find_user(conn, username):',
    '    query = f"SELECT * FROM users WHERE name = \'{username}\'"',
    '    return conn.execute(query).fetchall()',
  ].join('\n'),
  command: [
    'import subprocess',
    '',
    'def ping(host):',
    '    return subprocess.run("ping -c 1 " + host, shell=True, capture_output=True)',
  ].join('\n'),
  credential: [
    'DB_PASSWORD = "Pr0d-Admin-2026!"',
    '',
    'def connect(db):',
    '    return db.connect(user="admin", password=DB_PASSWORD)',
  ].join('\n'),
  benign: [
    'def average(values):',
    '    if not values:',
    '        return 0.0',
    '    return sum(values) / len(values)',
  ].join('\n'),
};

const CATEGORY_TEXT = {
  invalid_input: 'The code was rejected: it must be 1 to 20,000 characters and not only whitespace.',
  busy: 'Another analysis is still running. Wait for it to finish, then try again.',
  not_configured: 'Gemini is not configured on the server (GEMINI_API_KEY missing or rejected). No analysis was made.',
  quota: 'The Gemini quota or rate limit was reached. No analysis was made; try again later.',
  service_error: 'The Gemini service returned an error (for example, high demand). No analysis was made; try again later.',
  network_timeout: 'Gemini did not respond within 60 seconds or could not be reached. No analysis was made.',
  invalid_model_output: "Gemini returned output that failed the reviewer's validation, so it is not shown as findings.",
  payload_too_large: 'The request was larger than 64 KB.',
  forbidden_origin: 'The request was refused because it did not come from this page.',
  portal_unreachable: 'The portal server could not be reached.',
};

const SEVERITY_KIND = { High: 'fail', Medium: 'warn', Low: 'info' };

const $ = (id) => document.getElementById(id);
let running = false;

function codeIsSendable(code) {
  return code.trim().length > 0 && code.length <= MAX_CHARS;
}

function updateControls() {
  const code = $('rv-code').value;
  $('rv-count').textContent = `${code.length.toLocaleString('en-US')} / ${MAX_CHARS.toLocaleString('en-US')}`;
  $('rv-analyze').disabled = running || !codeIsSendable(code);
}

function setStatus(children) {
  $('rv-status').replaceChildren(...[].concat(children));
}

function setRaw(text) {
  $('rv-raw').querySelector('pre').textContent = text;
}

function findingCard(finding) {
  const kind = SEVERITY_KIND[finding.severity] ?? 'neutral';
  const severityClass = finding.severity in SEVERITY_KIND ? `sev-${finding.severity.toLowerCase()}` : 'sev-unknown';
  return el('article', { className: `card finding ${severityClass}` }, [
    el('div', { className: 'card-header' }, [el('h3', { text: finding.vulnerability }), badge(finding.severity, kind)]),
    el('p', { text: finding.description }),
    el('dl', { className: 'kv' }, [
      el('dt', { text: 'Evidence' }), el('dd', {}, el('code', { text: finding.evidence })),
      el('dt', { text: 'Remediation' }), el('dd', { text: finding.remediation }),
    ]),
  ]);
}

function renderFindings(result) {
  const holder = clear($('rv-findings'));
  const findings = Array.isArray(result.findings) ? result.findings : [];
  if (findings.length === 0) {
    holder.append(el('div', { className: 'callout' }, [
      el('p', { text: 'Analysis completed: no findings reported.' }),
      el('p', { className: 'small', text: 'This does not prove the code is secure. The model found nothing it could support with evidence from this snippet.' }),
    ]));
    return;
  }
  for (const finding of findings) holder.append(findingCard(finding));
}

function checkItem(label, passed, errors) {
  return el('li', {}, [
    passed ? badge('PASS', 'pass') : badge('FAIL', 'fail'),
    el('div', { className: 'check-detail' }, [
      el('strong', { text: label }),
      errors.length
        ? el('ul', { className: 'small' }, errors.map((error) => el('li', { text: error })))
        : el('div', { className: 'muted small', text: 'All checks passed.' }),
    ]),
  ]);
}

function renderLiveChecks(checks) {
  const holder = clear($('rv-live-checks'));
  if (!checks) {
    holder.append(el('p', { className: 'muted', text: 'No checks: the analysis did not complete.' }));
    return;
  }
  holder.append(el('ul', { className: 'check-list' }, [
    checkItem('Layer 1 · Schema (JSON structure, required fields, allowed severities)', checks.layer1.passed, checks.layer1.errors),
    checkItem('Layer 2 · Invariants (status, finding limit, exact evidence excerpts)', checks.layer2.passed, checks.layer2.errors),
    el('li', {}, [
      badge('N/A', 'neutral'),
      el('div', { className: 'check-detail' }, [
        el('strong', { text: 'Layer 3 · Semantic category: not applicable' }),
        el('div', { className: 'muted small', text: checks.layer3.reason }),
      ]),
    ]),
  ]));
}

function renderSuccess(data) {
  const count = data.result.findings?.length ?? 0;
  setStatus([
    badge('Completed', 'pass'),
    el('span', { text: `Analysis completed by ${data.model} in ${(data.elapsed_ms / 1000).toFixed(1)} s · ${count} finding${count === 1 ? '' : 's'}` }),
  ]);
  renderFindings(data.result);
  renderLiveChecks(data.live_checks);
  let pretty = data.raw;
  try {
    pretty = JSON.stringify(JSON.parse(data.raw), null, 2);
  } catch {
    // Show the raw text unchanged if it cannot be formatted.
  }
  setRaw(pretty);
}

function renderFailure(result) {
  const category = result.data?.error?.category ?? 'portal_unreachable';
  const message = CATEGORY_TEXT[category] ?? result.data?.error?.message ?? 'The request failed.';
  setStatus([badge(category.replaceAll('_', ' '), category === 'invalid_input' ? 'warn' : 'fail'), el('span', { text: message })]);
  clear($('rv-findings')).append(el('p', { className: 'muted', text: 'No findings shown: the analysis did not complete.' }));
  renderLiveChecks(null);
  setRaw(result.data ? JSON.stringify(result.data, null, 2) : `HTTP ${result.status}`);
}

async function analyze() {
  const code = $('rv-code').value;
  if (running || !codeIsSendable(code)) return;
  running = true;
  updateControls();
  setStatus([el('span', { className: 'spinner', attrs: { 'aria-hidden': 'true' } }), el('span', { text: 'Analysing with Gemini (live model call)…' })]);
  clear($('rv-findings')).append(el('p', { className: 'muted', text: 'Waiting for the model…' }));
  try {
    const result = await post('/api/part-1b/analyze', { code });
    if (result.ok && result.data?.result) renderSuccess(result.data);
    else renderFailure(result);
  } finally {
    running = false;
    updateControls();
  }
}

function init() {
  const textarea = $('rv-code');
  textarea.addEventListener('input', updateControls);
  textarea.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      analyze();
    }
  });
  $('rv-analyze').addEventListener('click', analyze);
  $('rv-clear').addEventListener('click', () => {
    textarea.value = '';
    updateControls();
    textarea.focus();
  });
  for (const button of $('rv-samples').querySelectorAll('button[data-sample]')) {
    button.addEventListener('click', () => {
      textarea.value = SAMPLES[button.dataset.sample] ?? '';
      updateControls();
    });
  }
  updateControls();
}

registerSection('part-1b', init);
