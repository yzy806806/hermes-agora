/* Auth state — JWT validation, login, logout, role visibility */
import { api } from './api.js';
import { ws } from './ws-client.js';

let userRole = null;

function checkAuth() {
  const token = api.getToken();
  if (!token) { showLogin(); return; }
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.exp * 1000 < Date.now()) { api.clearToken(); showLogin(); return; }
    userRole = payload.role || 'observer';
  } catch { api.clearToken(); showLogin(); return; }
  hideLogin();
  applyRoleVisibility();
  ws.connect(token);  // Phase 13.2b: always reconnect WS on auth check
}

function showLogin() {
  const el = document.getElementById('login-overlay');
  if (el) el.classList.remove('hidden');
}

function hideLogin() {
  const el = document.getElementById('login-overlay');
  if (el) el.classList.add('hidden');
}

function applyRoleVisibility() {
  const adminOnly = ['agents', 'plugins', 'audit'];
  if (userRole === 'admin') return;
  adminOnly.forEach(p => {
    const nav = document.querySelector(`#nav a[data-page="${p}"]`);
    if (nav) nav.style.display = userRole === 'agent' ? '' : 'none';
  });
}

async function login(username, password) {
  const res = await api.post('/auth/login', { username, password });
  api.setToken(res.token);
  userRole = res.role;
  hideLogin();
  applyRoleVisibility();
  ws.connect(res.token);
}

function logout() {
  ws.disconnect();
  api.clearToken();
  userRole = null;
  showLogin();
}

export const auth = { checkAuth, login, logout, getUserRole: () => userRole };
