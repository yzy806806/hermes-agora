/* Notification rendering — item HTML, badge update, list render */
const PRIORITY_COLORS = {
  critical: 'var(--danger)',
  high: '#f97316',
  medium: 'var(--warning)',
  low: 'var(--text-dim)',
};

function esc(s) {
  const d = document.createElement('span');
  d.textContent = s || '';
  return d.innerHTML;
}

function fmtTime(iso) {
  try { return new Date(iso).toLocaleString(); }
  catch { return iso; }
}

function renderItem(n, onRead) {
  const div = document.createElement('div');
  div.className = 'notif-item' + (n.read ? '' : ' unread');
  div.style.borderLeftColor = PRIORITY_COLORS[n.priority] || 'var(--accent)';
  div.innerHTML =
    `<div class="notif-title">${esc(n.title)}</div>` +
    `<div class="notif-body">${esc(n.body)}</div>` +
    `<div class="notif-meta">${fmtTime(n.created_at)} · ${n.type}</div>`;
  if (!n.read) {
    div.addEventListener('click', () => {
      onRead(n.id);
      div.classList.remove('unread');
    });
  }
  return div;
}

function renderBadge(count) {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  badge.textContent = count > 99 ? '99+' : count;
  badge.style.display = count > 0 ? 'flex' : 'none';
}

function renderList(items, onRead) {
  const list = document.getElementById('notif-list');
  if (!list) return;
  list.innerHTML = '';
  if (!items.length) {
    list.innerHTML = '<div class="notif-empty">No notifications</div>';
    return;
  }
  items.slice(0, 50).forEach(n => list.appendChild(renderItem(n, onRead)));
}

export const notifRender = { renderBadge, renderList };
