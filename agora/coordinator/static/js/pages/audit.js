/* Audit Log Viewer Page */
import { api } from '../api.js';

const COLORS = {
  auth:'#3b82f6', agent:'#34d399', permission:'#fbbf24',
  admin:'#f87171', token:'#a78bfa', system:'#94a3b8'
};
let offset = 0;
const LIMIT = 50;

export function mount(c) {
  c.innerHTML = `
    <h2>Audit Log</h2>
    <div id="af" style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <select id="f-type"><option value="">All Types</option>
        ${Object.keys(COLORS).map(t=>`<option value="${t}">${t}</option>`).join('')}
      </select>
      <input id="f-actor" placeholder="Actor" style="width:140px">
      <input id="f-action" placeholder="Action" style="width:140px">
      <input id="f-since" type="datetime-local" style="width:200px">
      <input id="f-until" type="datetime-local" style="width:200px">
      <button id="btn-afilter" class="secondary">Filter</button>
      <button id="btn-aexport" class="secondary">Export JSON</button>
    </div>
    <table><thead><tr>
      <th>Time</th><th>Type</th><th>Actor</th>
      <th>Action</th><th>Resource</th><th>Details</th>
    </tr></thead><tbody id="audit-tbody"></tbody></table>
    <div style="margin-top:12px;display:flex;gap:8px;align-items:center">
      <button id="btn-aprev" class="secondary">Prev</button>
      <span id="pager-info"></span>
      <button id="btn-anext">Next</button>
    </div>`;
  document.getElementById('btn-afilter').onclick=()=>{offset=0;load()};
  document.getElementById('btn-aprev').onclick=()=>{offset=Math.max(0,offset-LIMIT);load()};
  document.getElementById('btn-anext').onclick=()=>{offset+=LIMIT;load()};
  document.getElementById('btn-aexport').onclick=doExport;
  load();
}

export function unmount() { /* stateless — nothing to clean */ }

function buildParams() {
  const p = new URLSearchParams();
  p.set('limit', LIMIT); p.set('offset', offset);
  const v = (id, key) => { const x=document.getElementById(id).value; if(x) p.set(key, x); };
  v('f-type','event_type'); v('f-actor','actor_id'); v('f-action','action');
  const since = document.getElementById('f-since').value;
  const until = document.getElementById('f-until').value;
  if (since) p.set('since', new Date(since).toISOString());
  if (until) p.set('until', new Date(until).toISOString());
  return p;
}

async function load() {
  const tbody = document.getElementById('audit-tbody');
  try {
    const data = await api.get(`/admin/audit?${buildParams()}`);
    const events = data.events || [];
    const total = data.total ?? events.length;
    tbody.innerHTML = events.map(ev=>`<tr>
      <td style="white-space:nowrap;font-size:12px">${ev.timestamp||''}</td>
      <td><span style="color:${COLORS[ev.event_type]||'#fff'}">${ev.event_type}</span></td>
      <td>${ev.actor_id||'-'}</td><td>${ev.action||'-'}</td>
      <td>${ev.resource||'-'}</td>
      <td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis">${fmtD(ev.details)}</td>
    </tr>`).join('');
    document.getElementById('pager-info').textContent =
      `${offset+1}\u2013${Math.min(offset+LIMIT, total)} of ${total}`;
  } catch(e) { tbody.innerHTML=`<tr><td colspan="6">Error: ${e.message}</td></tr>`; }
}

function fmtD(d) { if(!d) return '-'; try{return JSON.stringify(d)}catch{return String(d)} }

async function doExport() {
  const p = buildParams(); p.delete('offset'); p.delete('limit');
  const data = await api.get(`/admin/audit?${p}`);
  const blob = new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `audit-${new Date().toISOString().slice(0,10)}.json`;
  a.click(); URL.revokeObjectURL(a.href);
}
