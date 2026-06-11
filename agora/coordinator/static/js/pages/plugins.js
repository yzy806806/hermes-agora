/* Plugin Management Page */
import { api } from '../api.js';

let clickHandler = null;

export function mount(c) {
  c.innerHTML = `
    <h2>Plugin Management</h2>
    <div style="margin-bottom:12px">
      <button id="btn-refresh-plugins" class="secondary">Refresh</button>
    </div>
    <table><thead><tr>
      <th>Name</th><th>Version</th><th>Status</th>
      <th>Health</th><th>Hooks</th><th>Actions</th>
    </tr></thead><tbody id="plugin-tbody"></tbody></table>`;
  document.getElementById('btn-refresh-plugins')
    .addEventListener('click', loadPlugins);
  loadPlugins();
}

export function unmount() {
  if (clickHandler) {
    document.removeEventListener('click', clickHandler);
    clickHandler = null;
  }
}

async function loadPlugins() {
  const tbody = document.getElementById('plugin-tbody');
  try {
    const data = await api.get('/admin/plugins');
    const plugins = data.plugins || data || [];
    tbody.innerHTML = plugins.map(p => `<tr>
      <td>${p.name}</td>
      <td>${p.version || '-'}</td>
      <td>${statusBadge(p.status)}</td>
      <td>${healthIcon(p.health)}</td>
      <td>${p.hook_count ?? (p.hooks?.length ?? 0)}</td>
      <td>${actionBtns(p)}</td>
    </tr>`).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="6">Error: ${e.message}</td></tr>`;
  }
}

function statusBadge(s) {
  const cls = { loaded:'badge-approved', disabled:'badge-offline',
    error:'badge-failed', enabled:'badge-approved' };
  return `<span class="badge ${cls[s]||''}">${s}</span>`;
}

function healthIcon(h) {
  if (h === 'healthy') return '✅';
  if (h === 'unhealthy') return '❌';
  return '–';
}

function actionBtns(p) {
  const n = encodeURIComponent(p.name);
  let b = '';
  if (p.status === 'loaded' || p.status === 'enabled')
    b += `<button class="danger btn-sm" data-pa="disable" data-pn="${n}">Disable</button> `;
  if (p.status === 'disabled')
    b += `<button class="btn-sm" data-pa="enable" data-pn="${n}">Enable</button> `;
  b += `<button class="secondary btn-sm" data-pa="reload" data-pn="${n}">Reload</button>`;
  return b;
}

clickHandler = async e => {
  const btn = e.target.closest('[data-pa]');
  if (!btn) return;
  const { pa, pn } = btn.dataset;
  try { await api.post(`/admin/plugins/${pn}/${pa}`); }
  catch (err) { alert(`Failed: ${err.message}`); return; }
  await loadPlugins();
};
document.addEventListener('click', clickHandler);
