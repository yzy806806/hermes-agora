/* HTTP fetch wrapper with JWT Authorization header */
const API_BASE = '/api/v1';

function getToken() {
  return sessionStorage.getItem('jwt');
}

function setToken(token) {
  if (token) sessionStorage.setItem('jwt', token);
  else sessionStorage.removeItem('jwt');
}

function clearToken() {
  sessionStorage.removeItem('jwt');
}

async function request(method, url, body, opts = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  
  const fetchOpts = { method, headers };
  if (body) fetchOpts.body = JSON.stringify(body);
  
  const res = await fetch(`${API_BASE}${url}`, fetchOpts);
  
  if (opts.raw) return res.text();
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getToken,
  setToken,
  clearToken,
  get: (url, opts) => request('GET', url, null, opts),
  post: (url, body) => request('POST', url, body),
  put: (url, body) => request('PUT', url, body),
  del: (url) => request('DELETE', url, null)
};
