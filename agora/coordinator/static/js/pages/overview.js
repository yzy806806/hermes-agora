/* Overview page — system stats, recent events, metrics chart */
import { api } from '../api.js';
import { ws } from '../ws-client.js';

let chart = null, unsubEvents = null;

export function mount(c) {
  // Ensure metrics chart canvas exists (not in static HTML)
  if (!$('metrics-chart')) {
    const wrap = document.createElement('div');
    wrap.className = 'card';
    wrap.innerHTML = '<canvas id="metrics-chart" height="250"></canvas>';
    c.appendChild(wrap);
  }
  loadStats(); loadEvents(); loadMetrics(); subscribeWS();
}

export function unmount() {
  if (unsubEvents) { unsubEvents(); unsubEvents = null; }
  if (chart) { chart.destroy(); chart = null; }
}

const $ = id => document.getElementById(id);
const setEl = (id, v) => { const e = $(id); if (e) e.textContent = v; };

async function loadStats() {
  const [m, a] = await Promise.all([api.get('/motions?limit=100'), api.get('/agents')]);
  setEl('s-motions', m.total ?? m.length ?? 0);
  setEl('s-agents', (Array.isArray(a) ? a : []).filter(x => x.is_online).length);
  try { const t = await api.get('/tasks?limit=1'); setEl('s-tasks', t.total ?? t.length ?? 0); }
  catch { setEl('s-tasks', '—'); }
}

async function loadEvents() {
  const e = await api.get('/events?limit=20');
  const el = $('event-stream'); if (!el) return;
  el.innerHTML = (e || []).map(renderEvent).join('');
}

function renderEvent(x) {
  return `<div class="event"><span class="time">${x.created_at||''}</span> ` +
    `<span class="detail">[${x.type}] ${x.detail}</span></div>`;
}

async function loadMetrics() {
  const t = await api.get('/metrics', { raw: true }).catch(() => '');
  if (typeof t !== 'string') return;
  const ls = [], vs = [];
  t.split('\n').filter(l => l && !l.startsWith('#')).forEach(l => {
    const [k, v] = l.split(' '); if (k && v) { ls.push(k); vs.push(parseFloat(v)); }
  });
  const ctx = $('metrics-chart'); if (!ctx) return;
  if (chart) chart.destroy();
  chart = new Chart(ctx.getContext('2d'), { type: 'bar',
    data: { labels: ls.slice(0,20), datasets: [{ label:'Value', data:vs.slice(0,20), backgroundColor:'#3b82f6' }] },
    options: { responsive:true, plugins:{legend:{labels:{color:'#e2e8f0'}}},
      scales:{ x:{ticks:{color:'#94a3b8',maxRotation:45}}, y:{ticks:{color:'#94a3b8'}} } }
  });
}

function subscribeWS() {
  unsubEvents = ws.on('EVENT', p => {
    const el = $('event-stream'); if (!el) return;
    el.insertAdjacentHTML('afterbegin', renderEvent({ created_at:p.timestamp, type:p.event_type, detail:p.detail }));
    while (el.children.length > 50) el.removeChild(el.lastChild);
  });
}
