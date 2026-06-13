/* Notification UI — bell icon, dropdown panel, filters */
import { notifications as store } from './notifications.js';
import { notifRender } from './notifications-render.js';

function $(id) { return document.getElementById(id); }

function refresh() {
  notifRender.renderBadge(store.getUnreadCount());
  notifRender.renderList(store.getNotifications(), store.markRead);
}

function applyFilters() {
  const pf = $('notif-filter-project');
  const prf = $('notif-filter-priority');
  store.setFilter(pf?.value || null, prf?.value || null);
}

function renderFilters() {
  const pf = $('notif-filter-project');
  const prf = $('notif-filter-priority');
  if (pf) pf.addEventListener('change', applyFilters);
  if (prf) prf.addEventListener('change', applyFilters);
}

function toggleDropdown() {
  const dd = $('notif-dropdown');
  if (dd) dd.classList.toggle('open');
}

function closeDropdown(e) {
  const dd = $('notif-dropdown');
  if (dd && !dd.contains(e.target)) dd.classList.remove('open');
}

function init() {
  const bell = $('notif-bell');
  if (bell) bell.addEventListener('click', (e) => {
    e.stopPropagation(); toggleDropdown();
  });
  document.addEventListener('click', closeDropdown);
  const markAll = $('notif-mark-all');
  if (markAll) markAll.addEventListener('click', () => store.markAllRead());
  store.setOnChange(refresh);
  store.init();
  renderFilters();
  refresh();
}

export const notifUI = { init };
