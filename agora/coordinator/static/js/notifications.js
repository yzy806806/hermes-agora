/* Notification data layer — fetch, mark-read, real-time WS handler */
import { api } from './api.js';
import { ws } from './ws-client.js';

let notifications = [];
let unreadCount = 0;
let filterProject = null;
let filterPriority = null;
let onChange = null;  // callback from UI layer

function setOnChange(cb) { onChange = cb; }

async function fetchNotifications() {
  try {
    const params = new URLSearchParams();
    if (filterProject) params.set('project_id', filterProject);
    if (filterPriority) params.set('priority', filterPriority);
    const res = await api.get(`/notifications?${params}`);
    notifications = res.notifications || [];
    unreadCount = notifications.filter(n => !n.read).length;
    onChange?.();
  } catch { /* silent — UI shows stale data */ }
}

async function markRead(notifId) {
  try {
    await api.post(`/notifications/${notifId}/read`);
    const n = notifications.find(x => x.id === notifId);
    if (n && !n.read) { n.read = true; unreadCount--; onChange?.(); }
  } catch { /* ignore */ }
}

async function markAllRead() {
  try {
    const params = filterProject
      ? `?project_id=${encodeURIComponent(filterProject)}` : '';
    await api.post(`/notifications/read-all${params}`);
    notifications.forEach(n => { n.read = true; });
    unreadCount = 0;
    onChange?.();
  } catch { /* ignore */ }
}

function handleWSNotification(payload) {
  if (!payload) return;
  notifications.unshift(payload);
  if (!payload.read) unreadCount++;
  if (notifications.length > 200) notifications.pop();
  onChange?.();
}

function setFilter(project, priority) {
  filterProject = project || null;
  filterPriority = priority || null;
  fetchNotifications();
}

function getNotifications() { return notifications; }
function getUnreadCount() { return unreadCount; }

function init() {
  ws.on('NOTIFICATION', handleWSNotification);
  fetchNotifications();
}

export const notifications = {
  init, setOnChange, fetchNotifications,
  markRead, markAllRead, setFilter,
  getNotifications, getUnreadCount,
};
