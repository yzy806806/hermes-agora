/* Metrics page — Chart.js dashboard (Phase 13.3c).
Loads DashboardCharts, fetches history, subscribes to WS events
and routes each event to the relevant chart via updateFromEvent(). */
import { DashboardCharts } from '../charts/index.js';
import { ws } from '../ws-client.js';

let dashCharts = null, unsubs = [];

export function mount() {
  dashCharts = new DashboardCharts();
  dashCharts.init();
  dashCharts.loadHistory();
  subscribeWS();
}

export function unmount() {
  unsubs.forEach(fn => fn()); unsubs = [];
  if (dashCharts) { dashCharts.destroy(); dashCharts = null; }
}

function subscribeWS() {
  const types = [
    'AGENT_STATUS', 'TASK_UPDATE', 'DISCUSSION_UPDATE',
    'PIPELINE_PHASE_CHANGE',
  ];
  types.forEach(t => {
    unsubs.push(ws.on(t, payload => {
      if (dashCharts) dashCharts.updateFromEvent({ type: t, payload });
    }));
  });
  // Phase 13.3c: wildcard catches any new event types with chart relevance
  unsubs.push(ws.on('*', msg => {
    if (dashCharts && msg.type) dashCharts.updateFromEvent(msg);
  }));
}
