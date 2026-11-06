// Evidence browser (FR-040, FR-041; task T050). File content is displayed as plain text.
import { get } from './api.js';
import { clear, el } from './dom.js';
import { loadEvidenceIndex, portalState, registerSection } from './registry.js';

const $ = (id) => document.getElementById(id);

function formatSize(bytes) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

function setPressed(id) {
  for (const button of $('evd-groups').querySelectorAll('.evidence-item')) {
    button.setAttribute('aria-pressed', String(button.dataset.evidenceId === id));
  }
}

async function openItem(id) {
  setPressed(id);
  const viewer = clear($('evd-viewer'));
  viewer.append(el('h2', { text: 'Viewer' }), el('p', { className: 'muted', text: 'Loading file…' }));
  const result = await get(`/api/evidence/${encodeURIComponent(id)}`);
  clear(viewer);
  if (!result.ok || !result.data) {
    viewer.append(el('h2', { text: 'Viewer' }), el('div', { className: 'callout callout-warn', text: result.data?.error?.message ?? 'File not found.' }));
    return;
  }
  const item = result.data;
  viewer.append(
    el('h2', { text: item.label }),
    el('dl', { className: 'kv viewer-meta' }, [
      el('dt', { text: 'Path' }), el('dd', {}, el('code', { text: item.path })),
      el('dt', { text: 'Size' }), el('dd', { text: `${formatSize(item.size_bytes)} (${item.size_bytes.toLocaleString('en-US')} bytes)` }),
      el('dt', { text: 'SHA-256' }), el('dd', {}, el('code', { className: 'small', text: item.sha256 })),
    ]),
    el('p', { className: 'hint', text: 'Content shown exactly as stored. On Windows, Get-FileHash -Algorithm SHA256 gives the same fingerprint.' }),
    el('pre', { text: item.content }),
  );
}

function renderGroups(index) {
  const holder = clear($('evd-groups'));
  for (const group of index.groups ?? []) {
    const list = el('ul', { className: 'evidence-list' });
    for (const item of group.items) {
      const button = el('button', {
        className: 'evidence-item',
        attrs: { type: 'button', 'data-evidence-id': item.id, 'aria-pressed': 'false' },
      }, [el('span', { text: item.label }), el('span', { className: 'path', text: item.path })]);
      button.addEventListener('click', () => openItem(item.id));
      list.append(el('li', {}, button));
    }
    holder.append(el('section', { className: 'evidence-group', attrs: { 'aria-label': group.title } }, [
      el('h3', { text: `${group.title} (${group.items.length})` }),
      list,
    ]));
  }
}

function applyFilter() {
  const term = $('evd-filter').value.trim().toLowerCase();
  for (const group of $('evd-groups').querySelectorAll('.evidence-group')) {
    let visible = 0;
    for (const row of group.querySelectorAll('.evidence-list li')) {
      const match = !term || row.textContent.toLowerCase().includes(term);
      row.hidden = !match;
      if (match) visible += 1;
    }
    group.hidden = visible === 0;
  }
}

function consumePending() {
  const id = portalState.pendingEvidenceId;
  if (!id || $('section-evidence').hidden) return;
  portalState.pendingEvidenceId = null;
  $('evd-filter').value = '';
  applyFilter();
  openItem(id);
  $('evd-groups').querySelector(`[data-evidence-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'center' });
}

async function init() {
  renderGroups(await loadEvidenceIndex(get));
  $('evd-filter').addEventListener('input', applyFilter);
  window.addEventListener('portal:open-evidence', consumePending);
  window.addEventListener('hashchange', () => window.setTimeout(consumePending, 0));
  consumePending();
}

registerSection('evidence', init);
