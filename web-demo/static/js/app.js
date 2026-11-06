// Router, theme, health badge and repository link (FR-001, FR-004, FR-054; task T020).
import { get } from './api.js';
import { clear, el } from './dom.js';
import { noteServerInstance, portalState, sections } from './registry.js';
import './part1a.js';
import './part1b.js';
import './evaluation.js';
import './evidence.js';
import './methodology.js';

const ROUTES = ['overview', 'methodology', 'part-1a', 'part-1b', 'evaluation', 'evidence'];
const TITLES = {
  overview: 'Project Overview',
  methodology: 'Assignment Methodology',
  'part-1a': 'Part 1A: Tiered Rate Limiter',
  'part-1b': 'Part 1B: AI Security Code Reviewer',
  evaluation: 'Evaluation Dashboard',
  evidence: 'Engineering Evidence',
};
const THEME_KEY = 'portal-theme';

function currentRoute() {
  const route = window.location.hash.replace(/^#/, '');
  return ROUTES.includes(route) ? route : 'overview';
}

function closeNav() {
  document.getElementById('sidebar').classList.remove('is-open');
  document.getElementById('nav-toggle').setAttribute('aria-expanded', 'false');
}

async function initSection(route) {
  const entry = sections.get(route);
  if (!entry || entry.initialised) return;
  entry.initialised = true;
  try {
    await entry.init();
  } catch (error) {
    entry.initialised = false;
    console.warn(`Section ${route} failed to initialise`, error);
  }
}

function show(route, moveFocus) {
  for (const name of ROUTES) {
    document.getElementById(`section-${name}`).hidden = name !== route;
  }
  for (const link of document.querySelectorAll('.nav-list a')) {
    if (link.dataset.route === route) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  document.getElementById('topbar-title').textContent = TITLES[route];
  document.title = `${TITLES[route]} · Assignment 1 Portal`;
  closeNav();
  if (moveFocus) document.getElementById(`h-${route}`).focus();
  initSection(route);
}

function storedTheme() {
  try {
    return window.localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function effectiveTheme() {
  const explicit = document.documentElement.dataset.theme;
  if (explicit) return explicit;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function updateThemeButton() {
  const next = effectiveTheme() === 'dark' ? 'light' : 'dark';
  const button = document.getElementById('theme-toggle');
  button.textContent = next === 'dark' ? 'Dark theme' : 'Light theme';
  button.setAttribute('aria-label', `Switch to ${next} theme`);
}

function setupTheme() {
  const saved = storedTheme();
  if (saved === 'dark' || saved === 'light') document.documentElement.dataset.theme = saved;
  updateThemeButton();
  document.getElementById('theme-toggle').addEventListener('click', () => {
    const next = effectiveTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // Theme preference is a convenience; ignore storage failures.
    }
    updateThemeButton();
  });
}

function renderRepositoryLinks(url) {
  for (const id of ['repo-link', 'overview-repo-link']) {
    const holder = document.getElementById(id);
    if (!holder) continue;
    clear(holder);
    if (url) holder.append(el('a', { text: url, attrs: { href: url, rel: 'noopener noreferrer' } }));
    else holder.append('Repository link not configured');
  }
}

async function loadHealth() {
  const badge = document.getElementById('health-badge');
  const result = await get('/api/health');
  if (!result.ok || !result.data) {
    badge.className = 'badge badge-fail';
    badge.textContent = 'Portal server unreachable';
    return;
  }
  const health = result.data;
  portalState.health = health;
  noteServerInstance(health.server_instance);
  const gemini = health.part1b?.configured;
  badge.className = `badge ${gemini ? 'badge-pass' : 'badge-warn'}`;
  badge.textContent = gemini ? 'Portal OK · Gemini configured' : 'Portal OK · Gemini not configured';
  badge.title = `Part 1A limiter ${health.part1a?.available ? 'available' : 'unavailable'}; model ${health.part1b?.model}`;
  renderRepositoryLinks(health.repository_url);
}

function setupNav() {
  const toggle = document.getElementById('nav-toggle');
  toggle.addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    const open = !sidebar.classList.contains('is-open');
    sidebar.classList.toggle('is-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (open) sidebar.querySelector('a[aria-current="page"], a').focus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeNav();
  });
}

setupTheme();
setupNav();
window.addEventListener('hashchange', () => show(currentRoute(), true));
show(currentRoute(), false);
loadHealth();
