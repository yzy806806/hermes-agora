# Phase 13 Architecture: Dashboard Enhancement

> See also: [DESIGN-phase13.md](DESIGN-phase13.md) Part B

## B1: Real-time WebSocket Push

**Before (Phase 11):** SSE (`/api/v1/events/stream`) for event updates. Dashboard WS (`/ws/dashboard`) used only for auth handshake.

**After (Phase 13):** Full WebSocket push replaces SSE. Dashboard WS stays open, receives events in real time.

```
Coordinator Event → dashboard_ws.py → fan-out → all subscribed dashboard WS clients
```

**Client-side:**
```javascript
const ws = new WebSocket(`ws://${location.host}/ws/dashboard?token=${jwt}`);
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
        case "DISCUSSION_UPDATE": case "TASK_UPDATE":
        case "AGENT_STATUS": case "PIPELINE_PHASE_CHANGE":
        case "NOTIFICATION": /* handle */
    }
};
```

**Changes:** `dashboard_ws.py` adds event fan-out; `dashboard.js` replaces EventSource with WebSocket + reconnection logic; SSE endpoint kept as fallback.

## B2: Charts (Metrics Visualization)

Chart.js-based visualizations (already a dependency from Phase 11):

| Chart | Type | Data Source |
|-------|------|-------------|
| Agent Activity Timeline | Line | Active agents over time |
| Task Throughput | Bar | Tasks completed per day/week |
| Discussion Metrics | Pie | Motion outcomes (consensus/deadlock/timeout) |
| Pipeline Success Rate | Gauge | % of pipelines that succeed |
| API Rate Limit Usage | Line | TPM usage per agent |

**New API:** `GET /api/v1/metrics/history?metric=agent_activity&range=7d` → Chart.js-compatible JSON

**New file:** `static/js/charts.js` — DashboardCharts class, updates from real-time WS events

## B3: Notification System

**Notification types:**

| Type | Trigger | Priority |
|------|---------|----------|
| PIPELINE_COMPLETED | Pipeline finishes | High |
| PIPELINE_FAILED | Pipeline fails | Critical |
| REVIEW_REQUESTED | Code review needed | Medium |
| AGENT_OFFLINE | Agent heartbeat lost | High |
| RATE_LIMITED | Agent hits TPM limit | Medium |
| DISCUSSION_DEADLOCK | Discussion deadlocks | Medium |

**NotificationManager:** Creates notification → stores in SQLite → pushes to dashboard WS clients (filtered by project subscription).

**Dashboard UI:** Bell icon + unread badge → dropdown panel → mark read / mark all read → filter by project/priority.

**API:**
```
GET    /api/v1/notifications?project_id=X&unread_only=true
POST   /api/v1/notifications/{id}/read
POST   /api/v1/notifications/read-all
```

## New Files

```
agora/coordinator/
├── notifications.py             # NotificationManager (~100 lines)
├── notification_models.py       # Notification model (~40 lines)
├── notification_router.py       # REST API routes (~60 lines)
├── storage/notifications.py     # Notification CRUD (~80 lines)
agora/coordinator/static/
├── js/charts.js                 # Chart.js visualizations (~200 lines)
├── js/notifications.js          # Notification UI logic (~120 lines)
└── js/ws_client.js              # WebSocket client (replaces SSE) (~80 lines)
```
