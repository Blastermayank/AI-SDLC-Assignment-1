// Shared state between the router (app.js) and section modules. Kept separate to avoid
// circular imports between app.js and the sections.

export const sections = new Map();

export const portalState = {
  serverInstance: null,
  health: null,
  evidenceIndex: null,
  pendingEvidenceId: null,
};

// Ask the Evidence section to open one item (used by links from other sections).
export function openEvidence(id) {
  portalState.pendingEvidenceId = id;
  if (window.location.hash !== '#evidence') window.location.hash = '#evidence';
  else window.dispatchEvent(new CustomEvent('portal:open-evidence'));
}

let evidenceIndexPromise = null;

// Shared, cached fetch of /api/evidence (used by the Evidence and Methodology sections).
export function loadEvidenceIndex(getter) {
  if (!evidenceIndexPromise) {
    evidenceIndexPromise = getter('/api/evidence').then((result) => {
      portalState.evidenceIndex = result.ok ? result.data : { groups: [] };
      return portalState.evidenceIndex;
    });
  }
  return evidenceIndexPromise;
}

export function registerSection(route, init) {
  sections.set(route, { init, initialised: false });
}

// Returns true when a response shows the server restarted since the page last saw it.
export function noteServerInstance(instance) {
  if (!instance) return false;
  const changed = portalState.serverInstance !== null && portalState.serverInstance !== instance;
  portalState.serverInstance = instance;
  return changed;
}
