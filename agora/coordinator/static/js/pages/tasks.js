/* Task Kanban Page — fetch graphs, render board, WS real-time updates */
import { api } from '../api.js';
import { ws } from '../ws-client.js';
import { KanbanBoard } from '../components/kanban-board.js';

let board = null, unsubTask = null, currentGraphId = null;

export function mount(container) {
  container.innerHTML = `
    <h2>Task Board</h2>
    <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
      <select id="graph-select"><option value="">All Tasks</option></select>
      <button id="btn-refresh" class="secondary">Refresh</button>
    </div>
    <div id="kanban-container"></div>
    <div id="task-modal" class="modal-overlay hidden"><div class="modal" id="task-detail"></div></div>`;
  document.getElementById('graph-select').onchange = loadTasks;
  document.getElementById('btn-refresh').onclick = loadTasks;
  document.getElementById('task-modal').onclick = e => {
    if (e.target.id === 'task-modal') e.target.classList.add('hidden');
  };
  board = new KanbanBoard(document.getElementById('kanban-container'), { onCardClick: showDetail });
  loadGraphs(); loadTasks(); subscribeWS();
}

export function unmount() {
  if (unsubTask) { unsubTask(); unsubTask = null; }
  if (board) { board.destroy(); board = null; }
}

async function loadGraphs() {
  try {
    const data = await api.get('/task-graphs');
    (data.graphs || data || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.id; opt.textContent = g.id.slice(0, 8);
      document.getElementById('graph-select').appendChild(opt);
    });
  } catch { /* ignore */ }
}

async function loadTasks() {
  try {
    currentGraphId = document.getElementById('graph-select').value;
    const params = currentGraphId ? `?graph_id=${currentGraphId}` : '';
    const data = await api.get(`/tasks${params}`);
    if (board) board.setCards(data.tasks || data || []);
  } catch (e) {
    const c = document.getElementById('kanban-container');
    if (c) c.innerHTML = `<div class="card">Error: ${e.message}</div>`;
  }
}

async function showDetail(taskId) {
  try {
    const t = await api.get(`/tasks/${taskId}`);
    document.getElementById('task-detail').innerHTML = `
      <h3>${t.title||taskId}</h3>
      <p><strong>Status:</strong> <span class="badge badge-${(t.status||'').toLowerCase()}">${t.status}</span></p>
      <p><strong>Assigned:</strong> ${t.assigned_to||'—'}</p>
      <p><strong>Deps:</strong> ${(t.depends_on||[]).join(', ')||'none'}</p>
      ${t.error?`<p style="color:var(--danger)"><strong>Error:</strong> ${t.error}</p>`:''}
      <div class="actions"><button class="secondary" onclick="this.closest('.modal-overlay').classList.add('hidden')">Close</button></div>`;
    document.getElementById('task-modal').classList.remove('hidden');
  } catch(e){ alert(`Failed: ${e.message}`); }
}

function subscribeWS() {
  ws.subscribe(['tasks']);
  unsubTask = ws.on('TASK_STATUS', p => {
    if (board && p.task_id) board.moveCard(p.task_id, p.status);
  });
}
