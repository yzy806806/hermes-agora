/* Overview page — system stats, recent events, mini activity chart.
Phase 13.3c: uses DashboardCharts.updateFromEvent() for WS→chart wiring. */
import { api } from '../api.js';
import { ws } from '../ws-client.js';
import { ActivityChart } from '../charts/activity-chart.js';
import { DashboardCharts } from '../charts/index.js';

let activityChart = null, dashCharts = null, unsubs = [];

export function mount(c) {
  ensureChartContainer(c);
  loadStats(); loadEvents(); loadActivityChart(); subscribeWS();
}
export function unmount() {
  unsubs.forEach(fn => fn()); unsubs = [];
  if (dashCharts) { dashCharts.destroy(); dashCharts = null; }
  else if (activityChart) { activityChart.destroy(); activityChart = null; }
}

const $ = id => document.getElementById(id);
const setEl = (id, v) => { const e = $(id); if (e) e.textContent = v; };

function ensureChartContainer(c) {
  if (!$('overview-activity-chart')) {
    const wrap = document.createElement('div');
    wrap.className = 'card';
    wrap.innerHTML = '<canvas id="overview-activity-chart" height="180"></canvas>';
    c.appendChild(wrap);
  }
}

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

async function loadActivityChart() {
  const canvas = $('overview-activity-chart'); if (!canvas) return;
  activityChart = new ActivityChart(canvas);
  activityChart.loadHistory();
  dashCharts = new DashboardCharts();
  dashCharts.charts.activity = activityChart;
}

function subscribeWS() {
  const addEvent = p => {
    const el = $('event-stream'); if (!el) return;
    el.insertAdjacentHTML('afterbegin',
      renderEvent({created_at:p.timestamp,type:p.event_type||p.type,detail:p.detail||p.title||''}));
    while (el.children.length > 50) el.removeChild(el.lastChild);
  };
  ['EVENT','DISCUSSION_UPDATE','TASK_UPDATE','AGENT_STATUS','PIPELINE_PHASE_CHANGE','NOTIFICATION']
    .forEach(t => unsubs.push(ws.on(t, addEvent)));
  // Phase 13.3c: unified chart updates via DashboardCharts.updateFromEvent()
  ['AGENT_STATUS','TASK_UPDATE','DISCUSSION_UPDATE','PIPELINE_PHASE_CHANGE']
    .forEach(t => unsubs.push(ws.on(t, payload => {
      if (dashCharts) dashCharts.updateFromEvent({ type: t, payload });
    })));
}
