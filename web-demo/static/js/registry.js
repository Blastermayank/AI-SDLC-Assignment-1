// Shared state between the router (app.js) and section modules. Kept separate to avoid
// circular imports between app.js and the sections.

export const sections = new Map();

export const portalState = {
  serverInstance: null,
  health: null,
  evidenceIndex: null,
};

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
