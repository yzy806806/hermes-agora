/* Discussions page — real-time viewer with WS subscription.
Phase 13.2b: uses DISCUSSION_UPDATE canonical type
(backward-compat via ws-client alias from legacy types). */
import { api } from '../api.js';
import { ws } from '../ws-client.js';

let currentMotion = null, unsubs = [];
const ROLE_COLORS = {proposer:'#f59e0b',participant:'#3b82f6',reviewer:'#8b5cf6',moderator:'#ef4444'};
const $ = id => document.getElementById(id);

export function mount(c) {
  c.innerHTML = `<h2>Discussion Detail</h2>
    <div class="card"><label>Motion: </label>
    <select id="motion-select"><option value="">-- select --</option></select>
    <span id="motion-status" style="margin-left:12px"></span></div>
    <div id="timeline" style="max-height:500px;overflow-y:auto"></div>
    <div id="vote-summary" class="card" style="margin-top:12px"></div>`;
  $('motion-select').onchange = onSelectMotion;
  loadMotionList(); subscribeWS();
}

export function unmount() { unsubs.forEach(fn => fn()); unsubs = []; currentMotion = null; }

async function loadMotionList() {
  const m = await api.get('/motions?limit=100');
  const s = $('motion-select'); if (!s) return;
  const list = m.motions || m || [];
  s.innerHTML = '<option value="">-- select --</option>' +
    list.map(x => `<option value="${x.id}">${x.title} (${x.status})</option>`).join('');
}

async function onSelectMotion() {
  const mid = $('motion-select')?.value; if (!mid) return;
  currentMotion = mid;
  await Promise.all([loadTimeline(mid), loadVotes(mid)]);
}

async function loadTimeline(mid) {
  const tl = await api.get(`/discussions/${mid}/timeline`);
  const el = $('timeline'); if (!el) return;
  el.innerHTML = (tl || []).map(renderEntry).join('');
  el.scrollTop = el.scrollHeight;
}

async function loadVotes(mid) {
  const v = await api.get(`/motions/${mid}/votes`).catch(() => null);
  const el = $('vote-summary'); if (!el) return;
  const sum = v?.summary || v;
  el.innerHTML = sum ? `<h3>Vote Summary</h3><pre>${JSON.stringify(sum,null,2)}</pre>` : '';
}

function renderEntry(x) {
  const c = ROLE_COLORS[x.role] || '#94a3b8', r = x.round_num ? ` [R${x.round_num}]` : '';
  return `<div class="event"><span class="time">${x.time||''}</span> ` +
    `<span class="detail">${r} <span style="color:${c}">${x.agent_id||''}</span>: ${x.content}</span></div>`;
}

function subscribeWS() {
  // Phase 13.2b: canonical DISCUSSION_UPDATE catches all discussion events
  unsubs.push(ws.on('DISCUSSION_UPDATE', p => {
    if (p.motion_id && p.motion_id !== currentMotion) return;
    if (p.content) {
      const el = $('timeline'); if (!el) return;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
      el.insertAdjacentHTML('beforeend',
        renderEntry({time:p.timestamp,agent_id:p.agent_id,content:p.content,round_num:p.round}));
      if (atBottom) el.scrollTop = el.scrollHeight;
    }
    if (p.status) {
      const el = $('motion-status'); if (el) el.textContent = p.status;
    }
    if (p.vote) loadVotes(currentMotion);
  }));
}
