// Safe DOM helpers (Constitution IV): every value is inserted as text, never parsed as HTML.

export function el(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  const { className, text, attrs } = options;
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (attrs) {
    for (const [name, value] of Object.entries(attrs)) {
      if (/^on/i.test(name)) throw new Error(`Event-handler attributes are not allowed: ${name}`);
      if (value === undefined || value === null || value === false) continue;
      node.setAttribute(name, value === true ? '' : String(value));
    }
  }
  for (const child of [].concat(children)) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function clear(node) {
  node.replaceChildren();
  return node;
}

export function badge(text, kind = 'neutral') {
  return el('span', { className: `badge badge-${kind}`, text });
}

export function formatPercent(value, digits = 1) {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(digits)}%` : '-';
}

export function formatTimestamp(iso) {
  if (!iso) return '-';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso);
  return date.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC').replace(/Z$/, ' UTC');
}

export function formatClock(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function resultBadge(passed) {
  return passed ? badge('PASS', 'pass') : badge('FAIL', 'fail');
}

export function statusBadge(status) {
  const kind = { PASS: 'pass', FAIL: 'fail', INCOMPLETE: 'warn', UNREADABLE: 'neutral' }[status] || 'neutral';
  return badge(status || 'UNKNOWN', kind);
}
