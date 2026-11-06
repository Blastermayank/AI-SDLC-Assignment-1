// Part 1A demonstration (FR-010 to FR-017; task T028). Every outcome shown here comes from
// a real HTTP response; nothing is predicted in the browser (Constitution V).
import { get, post } from './api.js';
import { badge, clear, el, formatClock, formatTimestamp } from './dom.js';
import { noteServerInstance, registerSection } from './registry.js';

const MAX_HISTORY = 200;
const history = [];
let tiers = [];

const $ = (id) => document.getElementById(id);

function formatRate(perMinute) {
  return `${Number(perMinute.toFixed(2))} / min`;
}

function formatInterval(perMinute) {
  const seconds = 60 / perMinute;
  return seconds >= 1 ? `${Number(seconds.toFixed(1))} s` : `${Math.round(seconds * 1000)} ms`;
}

function renderTiers() {
  const body = $('rl-tiers').querySelector('tbody');
  clear(body);
  for (const tier of tiers) {
    body.append(
      el('tr', {}, [
        el('td', { text: tier.name }),
        el('td', { className: 'num', text: tier.capacity }),
        el('td', { className: 'num', text: formatRate(tier.refill_per_minute) }),
        el('td', { className: 'num', text: formatInterval(tier.refill_per_minute) }),
      ]),
    );
  }
  const select = $('rl-tier');
  const selected = select.value;
  clear(select);
  for (const tier of tiers) {
    select.append(
      el('option', { text: `${tier.name} (capacity ${tier.capacity})`, attrs: { value: tier.name } }),
    );
  }
  if (tiers.some((tier) => tier.name === selected)) select.value = selected;
}

function tokenMeter(tokens, capacity) {
  if (typeof tokens !== 'number' || !capacity || capacity > 20) return null;
  const full = Math.floor(tokens + 1e-9);
  const meter = el('div', { className: 'token-meter', attrs: { 'aria-hidden': 'true' } });
  for (let i = 0; i < capacity; i += 1) meter.append(el('span', { className: `token${i < full ? ' is-full' : ''}` }));
  return meter;
}

function setOutcome(kind, title, lines, extra) {
  const box = $('rl-last-outcome');
  box.className = `outcome${kind ? ` is-${kind}` : ''}`;
  clear(box);
  box.append(el('div', { className: 'outcome-title' }, title));
  for (const line of lines) box.append(el('div', { className: 'small', text: line }));
  if (extra) box.append(extra);
}

function showNotice(text, kind = 'info') {
  const notice = $('rl-notice');
  notice.className = `callout${kind === 'info' ? '' : ` callout-${kind}`}`;
  notice.textContent = text;
  notice.hidden = false;
}

function renderHistory() {
  const body = $('rl-history');
  clear(body);
  if (history.length === 0) {
    body.append(el('tr', { className: 'empty-row' }, el('td', { text: 'No requests yet.', attrs: { colspan: 7 } })));
    return;
  }
  for (const row of history) {
    body.append(
      el('tr', { className: 'history-row' }, [
        el('td', { className: 'nowrap', text: row.time }),
        el('td', { text: row.clientId }),
        el('td', { text: row.tier }),
        el('td', {}, row.accepted ? badge('ACCEPTED', 'pass') : badge('REJECTED', 'fail')),
        el('td', { className: 'num', text: row.status }),
        el('td', { className: 'num', text: row.retryAfter ? `${row.retryAfter} s` : '-' }),
        el('td', { className: 'num', text: row.tokens }),
      ]),
    );
  }
}

function handleServerInstance(instance) {
  if (noteServerInstance(instance) && history.length > 0) {
    history.length = 0;
    renderHistory();
    showNotice('The portal server was restarted, so its rate-limit state starts fresh. Earlier rows from this page were cleared.', 'warn');
  }
}

function renderTierWarning(outcome) {
  const warning = $('rl-tier-warning');
  if (outcome.tier_mismatch) {
    warning.textContent = `Client "${outcome.client_id}" is registered on the ${outcome.registered_tier} tier (capacity ${outcome.capacity}) from its first request. Part 1A keeps that tier, so this request used the ${outcome.registered_tier} bucket, not ${outcome.requested_tier}.`;
    warning.hidden = false;
  } else {
    warning.hidden = true;
  }
}

function renderOutcome(result) {
  const outcome = result.data;
  const tokens = typeof outcome.tokens_remaining === 'number' ? outcome.tokens_remaining.toFixed(2) : '-';
  const bucket = `Client "${outcome.client_id}" · ${outcome.registered_tier} bucket · ${tokens} of ${outcome.capacity} tokens left`;
  if (outcome.accepted) {
    setOutcome('accepted', [badge('ACCEPTED', 'pass'), ` HTTP ${result.status}`], [bucket],
      tokenMeter(outcome.tokens_remaining, outcome.capacity));
    return;
  }
  const header = result.headers.get('Retry-After');
  setOutcome('rejected', [badge('REJECTED', 'fail'), ` HTTP ${result.status} ${outcome.detail || ''}`], [
    `Retry-After: ${header ?? '-'} s (from the server's response header)`,
    bucket,
  ], tokenMeter(outcome.tokens_remaining, outcome.capacity));
}

async function sendRequest(event) {
  event.preventDefault();
  const button = $('rl-send');
  button.disabled = true;
  const clientId = $('rl-client-id').value;
  const tier = $('rl-tier').value;
  try {
    const result = await post('/api/part-1a/request', { client_id: clientId, tier });
    const outcome = result.data;
    if (outcome && typeof outcome.accepted === 'boolean') {
      handleServerInstance(outcome.server_instance);
      history.unshift({
        time: formatClock(new Date(outcome.timestamp_utc)),
        clientId: outcome.client_id,
        tier: outcome.requested_tier,
        accepted: outcome.accepted,
        status: result.status,
        retryAfter: result.headers.get('Retry-After'),
        tokens: typeof outcome.tokens_remaining === 'number' ? outcome.tokens_remaining.toFixed(2) : '-',
      });
      history.length = Math.min(history.length, MAX_HISTORY);
      renderHistory();
      renderTierWarning(outcome);
      renderOutcome(result);
      return;
    }
    const error = outcome?.error;
    if (result.status === 422) {
      const fields = error?.fields?.length ? ` Check: ${error.fields.join(', ')}.` : '';
      setOutcome('error', [badge('Invalid input', 'warn'), ` HTTP ${result.status}`], [`${error?.message ?? 'The request was rejected.'}${fields}`]);
    } else {
      setOutcome('error', [badge('Request failed', 'warn'), result.status ? ` HTTP ${result.status}` : ''], [error?.message ?? 'Unexpected response.']);
    }
  } finally {
    button.disabled = false;
  }
}

async function resetDemo() {
  const result = await post('/api/part-1a/reset');
  if (!result.ok) {
    showNotice(result.data?.error?.message ?? 'Reset failed.', 'warn');
    return;
  }
  noteServerInstance(result.data.server_instance);
  history.length = 0;
  renderHistory();
  $('rl-tier-warning').hidden = true;
  setOutcome('', 'No request sent yet', ['Send a request to see the limiter\'s decision.']);
  showNotice(`Demonstration reset: ${result.data.clients_cleared} client bucket(s) cleared. Tier settings are unchanged.`);
}

function gateTable(gates) {
  return el('div', { className: 'table-wrap' }, el('table', {}, [
    el('thead', {}, el('tr', {}, [el('th', { text: 'Gate' }), el('th', { text: 'Command' }), el('th', { className: 'num', text: 'Exit code' }), el('th', { text: 'Result' })])),
    el('tbody', {}, gates.map((gate) => el('tr', {}, [
      el('td', { text: gate.name }),
      el('td', {}, el('code', { text: gate.command })),
      el('td', { className: 'num', text: gate.exit_code }),
      el('td', {}, badge(gate.result, gate.result === 'PASS' ? 'pass' : 'fail')),
    ]))),
  ]));
}

async function loadHarness() {
  const holder = $('rl-harness');
  const result = await get('/api/part-1a/harness');
  clear(holder);
  const data = result.data;
  if (!result.ok || !data?.available) {
    holder.append(el('p', { className: 'muted', text: 'No saved harness results.' }));
    return;
  }
  const summary = data.summary;
  $('rl-harness-badge').replaceChildren(badge(`Latest run: ${summary.result}`, summary.result === 'PASS' ? 'pass' : 'fail'));
  holder.append(
    el('dl', { className: 'kv' }, [
      el('dt', { text: 'Run (UTC)' }), el('dd', { text: formatTimestamp(summary.timestamp_utc) }),
      el('dt', { text: 'Python' }), el('dd', { text: summary.python ?? '-' }),
      el('dt', { text: 'Tools' }), el('dd', { text: Object.entries(summary.tools ?? {}).map(([k, v]) => `${k} ${v}`).join(', ') || '-' }),
    ]),
    el('div', { className: 'section-block' }, gateTable(summary.gates ?? [])),
  );
  const details = el('div', { className: 'section-block' });
  for (const [name, text] of Object.entries(data.transcripts ?? {})) {
    details.append(el('details', {}, [el('summary', { text: `Transcript: ${name}` }), el('div', { className: 'details-body' }, el('pre', { text }))]));
  }
  holder.append(details);
  if ((data.history ?? []).length > 1) {
    holder.append(
      el('h3', { className: 'section-block', text: 'All saved runs (newest first)' }),
      el('div', { className: 'chip-list' }, data.history.map((run) => el('span', { className: 'chip' }, [
        run.run, badge(run.result, run.result === 'PASS' ? 'pass' : 'fail'),
      ]))),
      el('p', { className: 'hint', text: 'Each saved run is listed in the Engineering Evidence section with its unedited transcripts.' }),
    );
  }
}

async function init() {
  $('rl-form').addEventListener('submit', sendRequest);
  $('rl-reset').addEventListener('click', resetDemo);
  const result = await get('/api/part-1a/tiers');
  if (result.ok && Array.isArray(result.data)) {
    tiers = result.data;
    renderTiers();
  }
  await loadHarness();
}

registerSection('part-1a', init);
