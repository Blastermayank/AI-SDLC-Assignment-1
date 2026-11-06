// Fetch wrapper: resolves for every HTTP status so expected outcomes (e.g. HTTP 429) are
// rendered from the real server response instead of being treated as browser failures.

export async function request(method, path, body) {
  const init = { method, headers: { Accept: 'application/json' }, cache: 'no-store' };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, init);
  } catch {
    return {
      ok: false,
      status: 0,
      headers: new Headers(),
      data: { error: { category: 'portal_unreachable', message: 'The portal server could not be reached.' } },
    };
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  return { ok: response.ok, status: response.status, headers: response.headers, data };
}

export const get = (path) => request('GET', path);
export const post = (path, body = {}) => request('POST', path, body);

export function errorMessage(result, fallback = 'The request failed.') {
  return result?.data?.error?.message || fallback;
}
