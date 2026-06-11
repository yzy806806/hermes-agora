# DESIGN-phase11.md — Phase 11: Web Dashboard

> Version: v0.11.0-draft | Date: 2026-06-11 | Author: planner

## Background

Phase 1-10 delivered a full-featured Agora platform: discussion engine, task
execution (sequential + parallel), agent registration protocol, API rate
limiting, RBAC, audit logging, and a plugin ecosystem. v0.10.0 is released
with 866 tests passing.

The current dashboard (Phase 8.3) is a single-file HTML+JS proof-of-concept
with 4 tabs (Overview, Discussions, Agents, Metrics). It uses SSE for event
streaming and Chart.js CDN for metrics visualization. It works but is minimal:

- No real-time discussion viewer (SSE is one-directional, polling-based)
- No task kanban view (Phase 9.2 task engine has no UI)
- No agent management (approve/reject/suspend/config)
- No plugin management page
- No audit log viewer
- No dashboard auth (anyone can access /dashboard)
- Single monolithic JS file (hard to extend)

This design covers the full dashboard upgrade, building on existing Phase 8.3
code and integrating with Phase 10 features (RBAC, plugins, parallel exec).

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Dashboard Architecture | ★★★★★ | ★★★★★ | ★★★★ | Medium | **Phase 11 Core** |
| Real-time Discussion Viewer | ★★★★★ | ★★★★★ | ★★★★ | Medium | **Phase 11 Core** |
| Task Kanban View | ★★★★★ | ★★★★ | ★★★★ | Medium | **Phase 11 Core** |
| Agent Management Panel | ★★★★ | ★★★★ | ★★★★★ | Low | **Phase 11 Core** |
| Plugin Management Page | ★★★★ | ★★★ | ★★★★ | Low | **Phase 11 Core** |
| Audit Log Viewer | ★★★★ | ★★★ | ★★★★★ | Low | **Phase 11 Core** |
| RBAC Integration (Login) | ★★★★ | ★★★★ | ★★★★★ | Medium | **Phase 11 Core** |
| Mobile Responsive | ★★★ | ★★ | ★★★★ | Low | Phase 11 Stretch |

### Why these seven together

1. Architecture is the foundation — without a modular structure, adding 6 new
   pages becomes unmaintainable
2. Real-time viewer + Task kanban are the two highest-value features for users
   observing agent work
3. Agent/Plugin/Audit management all depend on RBAC — login must come first
4. All seven are needed to graduate the dashboard from "dev tool" to
   "production operations console"

## Architecture Target (end of Phase 11)

```
                        ┌─────────────────────────────────────────┐
                        │           Agora Platform v0.11           │
                        │  ┌──────────────────────────────────────┐ │
                        │  │         REST API + WebSocket Hub      │ │
                        │  └────────────────┬─────────────────────┘ │
                        │  ┌────────────────┴─────────────────────┐ │
                        │  │  ┌───────────┐ ┌──────────────────┐  │ │
                        │  │  │  RBAC     │ │  Dashboard API   │  │ │
                        │  │  │  Middle-  │ │  (new endpoints) │  │ │
                        │  │  │  ware     │ │  - audit query   │  │ │
                        │  │  └───────────┘ │  - task query    │  │ │
                        │  │  ┌───────────┐ │  - plugin list   │  │ │
                        │  │  │  Plugin   │ │  - agent config  │  │ │
                        │  │  │  Manager  │ │  - JWT login     │  │ │
                        │  │  └───────────┘ └──────────────────┘  │ │
                        │  │  ┌──────────────────────────────┐    │ │
                        │  │  │  Static Dashboard (HTML/JS)  │    │ │
                        │  │  │  - modular ES modules        │    │ │
                        │  │  │  - WebSocket real-time       │    │ │
                        │  │  │  - Chart.js CDN              │    │ │
                        │  │  └──────────────────────────────┘    │ │
                        │  └───────────────────────────────────────┘ │
                        └────────────────────┬──────────────────────┘
                                             │ HTTP/WS
                  ┌──────────────────────────┼──────────────────────────┐
                  ↓                          ↓                          ↓
             ┌─────────┐              ┌─────────┐              ┌─────────┐
             │ Browser │              │ Hermes  │              │ Docker  │
             │ (Human) │              │ Agent   │              │ Agent   │
             └─────────┘              └─────────┘              └─────────┘
```

## Part A: Dashboard Architecture

### A.1 Tech Selection

**Decision: Enhanced pure HTML/JS with ES modules, no framework.**

Evaluation:

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Pure HTML/JS (current) | Zero deps, simple | Hard to scale, single file | **Keep but modularize** |
| React/Vue/Svelte | Rich ecosystem, components | Requires npm, build step, bundle | ❌ Violates "no npm" constraint |
| HTMX | Lightweight, server-driven | Limited for real-time WS, no complex state | ❌ Not suited for kanban + WS |
| Alpine.js | Tiny (15KB), CDN, reactive | Limited component model | ⚠️ Viable but adds dep |
| **Vanilla JS ES modules** | Zero build, native browser support, modular | Manual DOM management | ✅ **Chosen** |

Rationale:
- Agora is a standalone Python package — no npm, no Node.js, no build step
- ES modules (`<script type="module">`) are supported in all modern browsers
  (Chrome 61+, Firefox 60+, Safari 11+, Edge 16+)
- We already use Chart.js via CDN — this pattern continues
- The dashboard is an operations console, not a consumer app — vanilla JS is
  sufficient for form-based CRUD + real-time display
- Modularizing into separate JS files (one per page) makes the codebase
  maintainable without a framework

### A.2 File Structure

```
agora/coordinator/static/
├── dashboard.html          # Shell: nav, page containers, login overlay
├── css/
│   └── dashboard.css       # Extracted from inline <style> in HTML
├── js/
│   ├── app.js              # Entry: router, auth, WS connection, nav
│   ├── api.js              # HTTP fetch wrapper with JWT auth header
│   ├── ws-client.js        # WebSocket client with reconnect
│   ├── pages/
│   │   ├── overview.js     # System overview + event stream
│   │   ├── discussions.js  # Real-time discussion viewer
│   │   ├── tasks.js        # Task kanban board
│   │   ├── agents.js       # Agent management panel
│   │   ├── plugins.js      # Plugin management page
│   │   └── audit.js        # Audit log viewer
│   └── components/
│       ├── kanban-board.js # Reusable kanban column/board component
│       ├── event-feed.js   # Reusable real-time event feed
│       └── modal.js        # Confirm/action modal
```

### A.3 Navigation

Pages (replacing current 4-tab nav):

| Tab | Route Hash | Description |
|---|---|---|
| Overview | `#overview` | System stats, recent events, agent status summary |
| Discussions | `#discussions` | Real-time discussion viewer with message feed |
| Tasks | `#tasks` | Kanban board showing task DAG + execution status |
| Agents | `#agents` | Agent list, approve/reject, config (TPM, concurrency) |
| Plugins | `#plugins` | Plugin list, enable/disable, health status |
| Audit | `#audit` | Audit log with filters (actor, action, type, time) |

Hash-based routing (`window.location.hash`) — no server-side routing needed.

### A.4 CSS Strategy

Extract inline styles from dashboard.html into `css/dashboard.css`. Keep the
dark theme (bg `#0f172a`, cards `#1e293b`). Add:

- Kanban board layout (flex columns, draggable cards)
- Modal/overlay styles (login, confirm dialogs)
- Form styles (inputs, toggles, buttons)
- Responsive breakpoints (mobile-friendly sidebar collapse)
- Status badges (online/offline, pending/approved/rejected)

## Part B: Real-time Discussion Viewer

### B.1 Current State

Phase 8.3 dashboard uses SSE (`/api/v1/events/stream`) which polls every 2
seconds. This is:
- One-directional (server → client only)
- Polling-based (2s latency)
- No message send capability

### B.2 Design: WebSocket Upgrade

Add a dedicated dashboard WebSocket endpoint:

```
GET /ws/dashboard
```

The dashboard WS is separate from agent WS (`/ws/{agent_id}`) because:
- Dashboard is a human viewer, not an agent
- Different message types (read-only observation vs task execution)
- Different auth (JWT login vs agent token)

**Connection flow:**

```
Browser                    Agora
  │                          │
  │── POST /api/v1/auth/login (username + password)
  │                          │── validate, return JWT
  │── GET /ws/dashboard?token=<jwt>
  │                          │── validate JWT, upgrade to WS
  │←── {type: "WELCOME", payload: {role, tenant_id}}
  │                          │
  │── {type: "SUBSCRIBE", payload: {channels: ["discussions", "tasks", "events"]}}
  │←── {type: "SUBSCRIBED", payload: {channels: [...]}}
  │                          │
  │   ... real-time messages flow ...
```

**Message types (server → dashboard):**

```json
// Discussion messages
{"type": "DISCUSSION_MESSAGE", "payload": {"motion_id": "...", "agent_id": "...", "content": "...", "round": 3, "timestamp": "..."}}

// Motion state changes
{"type": "MOTION_STATUS", "payload": {"motion_id": "...", "status": "voting", "timestamp": "..."}}

// Vote events
{"type": "VOTE_CAST", "payload": {"motion_id": "...", "agent_id": "...", "vote": "approve", "timestamp": "..."}}

// Task events
{"type": "TASK_STATUS", "payload": {"task_id": "...", "status": "running", "agent_id": "...", "timestamp": "..."}}

// Agent events
{"type": "AGENT_ONLINE", "payload": {"agent_id": "...", "timestamp": "..."}}
{"type": "AGENT_OFFLINE", "payload": {"agent_id": "...", "reason": "timeout", "timestamp": "..."}}

// System events
{"type": "EVENT", "payload": {"event_type": "...", "detail": "...", "timestamp": "..."}}
```

### B.3 Discussion Viewer Page

Features:
- Motion selector (dropdown, like current)
- Real-time message feed (auto-scroll, new messages appear at bottom)
- Agent name badges with role colors
- Round markers
- Vote summary panel (live updating)
- Discussion status indicator (discussing → voting → closed)

Implementation: `js/pages/discussions.js` subscribes to `discussions` channel,
renders messages into a scrollable feed. Uses `IntersectionObserver` to
auto-scroll only when user is at bottom.

## Part C: Task Kanban View

### C.1 Data Model Integration

Phase 9.2 task models (`task_models.py`) provide:
- `TaskNode`: id, title, status, assigned_to, depends_on, artifact_paths
- `TaskGraph`: id, motion_id, tasks[], parallel_mode, max_parallel_slots
- `TaskStatus`: pending → assigned → running → done/accepted/rejected/failed

Phase 10 adds:
- `ExecutionSlot`: task_id, agent_id, started_at, status
- `ConflictReport`: task_a, task_b, resource, severity

### C.2 New API Endpoints

```
GET  /api/v1/tasks                    # List all tasks (filter: ?graph_id=, ?status=, ?agent_id=)
GET  /api/v1/tasks/{task_id}          # Single task detail
GET  /api/v1/task-graphs              # List all task graphs
GET  /api/v1/task-graphs/{graph_id}   # Single graph with all tasks + deps
GET  /api/v1/execution-slots          # Current execution slots (who's running what)
```

All endpoints require `@requires(Permission.CONFIG_READ)` (observer+ can view).

### C.3 Kanban Board Layout

```
┌──────────────────────────────────────────────────────────────┐
│ Task Board: graph-abc123  [parallel: auto] [slots: 3/10]    │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ PENDING  │ ASSIGNED │ RUNNING  │ DONE     │ FAILED          │
│ (3)      │ (2)      │ (2)      │ (5)      │ (1)             │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────┐        │
│ │Task A│ │ │Task C│ │ │Task D│ │ │Task B│ │ │Task X│        │
│ │dep:B │ │ │agent:│ │ │agent:│ │ │done  │ │ │err:..│        │
│ │      │ │ │ coder│ │ │review│ │ │2m ago│ │ │retry │        │
│ └──────┘ │ └──────┘ │ └──────┘ │ └──────┘ │ └──────┘        │
│ ┌──────┐ │          │ ┌──────┐ │ ┌──────┐ │                 │
│ │Task E│ │          │ │Task F│ │ │Task G│ │                 │
│ │dep:A │ │          │ │      │ │ │      │ │                 │
│ └──────┘ │          │ └──────┘ │ └──────┘ │                 │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

Each card shows:
- Task title
- Dependency count (blocked by N)
- Assigned agent (if any)
- Status badge (color-coded)
- Duration (if running/done)
- Retry count (if > 0)

Clicking a card opens detail panel: description, full dependency list,
artifact paths, error message (if failed), execution history.

### C.4 Real-time Updates

Kanban subscribes to `tasks` channel via dashboard WS. On `TASK_STATUS`
messages, moves cards between columns. DAG dependency visualization is a
stretch goal (Phase 11.5+).

### C.5 DAG Visualization (Stretch)

For graphs with >3 tasks, show a mini DAG at the top using a simple SVG/Canvas
renderer. Not required for Phase 11 core — can be added later.

## Part D: Agent Management Panel

### D.1 Current State

Phase 9.3 added admin endpoints:
- `GET /api/v1/admin/agents` — list all with approval status
- `POST /api/v1/admin/agents/{id}/approve`
- `POST /api/v1/admin/agents/{id}/reject`
- `POST /api/v1/admin/agents/{id}/suspend`

Phase 10.2 added RBAC — these endpoints are gated behind `@requires`.

### D.2 New API Endpoints

```
PUT  /api/v1/admin/agents/{agent_id}/config   # Update agent config (TPM, concurrency, role)
POST /api/v1/admin/agents/{agent_id}/token    # Rotate agent token
```

Config update payload:
```json
{
  "tpm_limit": 20000,
  "tpm_burst_factor": 1.5,
  "max_concurrent_tasks": 3,
  "role": "agent",
  "allowed_discussion_roles": ["participant", "reviewer"]
}
```

### D.3 Agent Management Page

Features:
- Agent table (like current) with added columns:
  - Approval status (pending/approved/rejected) with action buttons
  - Role (admin/agent/observer) with dropdown to change
  - TPM limit with inline edit
  - Max concurrent tasks with inline edit
  - Active tasks count (clickable → filters kanban)
  - Online status (🟢/🔴)
- Approve/Reject buttons for pending agents
- Suspend/Unsuspend toggle
- Token rotation button (with confirmation modal)
- Search/filter by name, type, status

### D.4 Agent Registration Flow (Dashboard View)

When a new agent registers and `AGORA_REQUIRE_APPROVAL=true`:
1. Agent appears in dashboard with "pending" badge
2. Admin reviews agent info (name, type, capabilities)
3. Admin clicks Approve or Reject
4. Dashboard sends POST to `/api/v1/admin/agents/{id}/approve`
5. Agent list updates in real-time via WS

## Part E: Plugin Management Page

### E.1 Current State

Phase 10.3 plugin system provides:
- `PluginCoordinator` with load/unload/health_check
- `PluginManifest` with name, version, hook_points
- Plugin discovery via entry points
- Sandbox with import blocking + timeouts

No REST API exists for plugin management yet.

### E.2 New API Endpoints

```
GET    /api/v1/admin/plugins                  # List loaded plugins with status
GET    /api/v1/admin/plugins/{name}           # Plugin detail (manifest, hooks, health)
POST   /api/v1/admin/plugins/{name}/reload    # Reload a plugin
POST   /api/v1/admin/plugins/{name}/disable   # Unload a plugin
POST   /api/v1/admin/plugins/{name}/enable    # Load a plugin
GET    /api/v1/admin/plugins/available        # List discoverable but not loaded plugins
```

All endpoints require `@requires(Permission.ADMIN_FULL)`.

### E.3 Plugin Management Page

Features:
- Plugin table: name, version, status (loaded/disabled/error), hook count
- Enable/Disable toggle per plugin
- Reload button
- Health status indicator (✅/❌ from health_check)
- Available plugins list (discovered but not loaded)
- Plugin detail panel: manifest info, registered hooks, dependencies

## Part F: Audit Log Viewer

### F.1 Current State

Phase 10.2c `AuditLogger` provides:
- `log_event(event: AuditEvent)` — write to audit_log table
- `query_events(actor_id, action, event_type, tenant_id, since, until, limit)`

No REST API exposes audit logs yet.

### F.2 New API Endpoints

```
GET /api/v1/admin/audit   # Query audit log with filters
```

Query parameters:
- `actor_id` — filter by actor
- `action` — filter by action name
- `event_type` — auth/agent/permission/token/admin/system
- `tenant_id` — filter by tenant
- `since` — ISO timestamp
- `until` — ISO timestamp
- `limit` — max results (default 100)
- `offset` — pagination

Requires `@requires(Permission.ADMIN_FULL)`.

Response:
```json
{
  "events": [
    {
      "id": 1,
      "event_type": "auth",
      "actor_id": "admin",
      "actor_role": "admin",
      "action": "login",
      "resource": "dashboard",
      "details": {"ip": "192.168.1.1"},
      "timestamp": "2026-06-11T12:00:00Z",
      "tenant_id": "default"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

### F.3 Audit Log Viewer Page

Features:
- Table with columns: timestamp, event_type, actor, action, resource, details
- Filter bar: event_type dropdown, actor search, action search, date range
- Pagination (prev/next)
- Click row to expand details JSON
- Export button (download as JSON) — stretch goal
- Color-coded event types (auth=blue, agent=green, permission=orange, admin=red)

## Part G: RBAC Integration (Dashboard Login)

### G.1 Current State

Dashboard is currently unauthenticated — anyone with network access to the
Agora server can view `/dashboard`. Phase 10.2 provides JWT token management
but only for agent auth.

### G.2 Design: Dashboard Login

Add human user authentication:

```
POST /api/v1/auth/login
```

Request:
```json
{
  "username": "admin",
  "password": "agora-dashboard-password"
}
```

Response:
```json
{
  "token": "eyJ...",
  "role": "admin",
  "expires_in": 3600
}
```

Implementation:
- Credentials stored in `AGORA_DASHBOARD_USERS` env var:
  `AGORA_DASHBOARD_USERS=admin:hashedpassword,viewer:hashedpassword2`
- Passwords hashed with bcrypt (add `bcrypt` as optional dependency)
- If `AGORA_DASHBOARD_USERS` is not set, dashboard remains open (backward compat)
- JWT issued with `agent_id="dashboard_user:<username>"`, role from config
- Dashboard JS stores JWT in `sessionStorage`, attaches to all API calls via
  `Authorization: Bearer <token>` header

### G.3 Login Flow

```
1. User opens /dashboard
2. JS checks sessionStorage for existing JWT
3. If no JWT or expired → show login overlay
4. User enters username + password
5. POST /api/v1/auth/login → receive JWT
6. Store JWT, hide overlay, connect WS with JWT
7. All subsequent API calls include Authorization header
8. WS connection includes ?token=<jwt> parameter
```

### G.4 Role-Based UI

Dashboard UI adapts based on JWT role:
- `admin`: all pages visible, all actions available
- `agent`: Overview + Discussions + Tasks (read-only for agent config)
- `observer`: Overview + Discussions (read-only)

Pages hidden for non-admin roles: Agents (config), Plugins, Audit.

### G.5 Backward Compatibility

If `AGORA_DASHBOARD_USERS` is not set:
- `/api/v1/auth/login` returns 501 (not configured)
- Dashboard loads without login overlay
- All pages visible (no role check)
- Existing behavior preserved

## API Summary

### New Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| POST | `/api/v1/auth/login` | public | Dashboard user login |
| GET | `/api/v1/tasks` | config:read | List tasks |
| GET | `/api/v1/tasks/{id}` | config:read | Task detail |
| GET | `/api/v1/task-graphs` | config:read | List task graphs |
| GET | `/api/v1/task-graphs/{id}` | config:read | Graph with tasks |
| GET | `/api/v1/execution-slots` | config:read | Current execution slots |
| PUT | `/api/v1/admin/agents/{id}/config` | admin:full | Update agent config |
| POST | `/api/v1/admin/agents/{id}/token` | admin:full | Rotate agent token |
| GET | `/api/v1/admin/plugins` | admin:full | List loaded plugins |
| GET | `/api/v1/admin/plugins/{name}` | admin:full | Plugin detail |
| POST | `/api/v1/admin/plugins/{name}/reload` | admin:full | Reload plugin |
| POST | `/api/v1/admin/plugins/{name}/disable` | admin:full | Unload plugin |
| POST | `/api/v1/admin/plugins/{name}/enable` | admin:full | Load plugin |
| GET | `/api/v1/admin/plugins/available` | admin:full | Discoverable plugins |
| GET | `/api/v1/admin/audit` | admin:full | Query audit log |

### New WebSocket Endpoint

| Path | Auth | Description |
|---|---|---|
| `/ws/dashboard` | JWT (query param) | Dashboard real-time feed |

### Modified Files

| File | Change |
|---|---|
| `main.py` | Add `/ws/dashboard` route, auth endpoints, plugin/task/audit routers |
| `router.py` | Add task query endpoints, agent config endpoints |
| `dashboard.py` | Add plugin list, audit query endpoints |
| `models.py` | Add `DashboardLoginRequest`, `AgentConfigUpdate`, `AuditQueryResponse` |
| `ws_handlers.py` | Add dashboard WS message types |
| `static/dashboard.html` | Rewrite: modular shell, login overlay, 6-tab nav |
| `static/dashboard.js` | Split into `js/` modules |
| `static/css/dashboard.css` | New: extracted styles + new components |

### New Files

| File | Description |
|---|---|
| `static/js/app.js` | Entry point, router, auth, WS |
| `static/js/api.js` | HTTP fetch wrapper |
| `static/js/ws-client.js` | WebSocket client |
| `static/js/pages/overview.js` | Overview page |
| `static/js/pages/discussions.js` | Discussion viewer |
| `static/js/pages/tasks.js` | Task kanban |
| `static/js/pages/agents.js` | Agent management |
| `static/js/pages/plugins.js` | Plugin management |
| `static/js/pages/audit.js` | Audit log viewer |
| `static/js/components/kanban-board.js` | Kanban component |
| `static/js/components/event-feed.js` | Event feed component |
| `static/js/components/modal.js` | Modal component |
| `static/css/dashboard.css` | Stylesheet |

## Sub-Task Breakdown

### 11.1 Dashboard Backend API (dev-merger, ~4 tasks)

**11.1a Task query endpoints** — `GET /api/v1/tasks`, `/task-graphs`,
`/execution-slots`. Wire into `storage/tasks.py`. Add Pydantic response models.

**11.1b Agent config endpoints** — `PUT /admin/agents/{id}/config`,
`POST /admin/agents/{id}/token`. Wire into `storage/agents.py` + `token_manager.py`.

**11.1c Plugin management endpoints** — `GET /admin/plugins` etc. Wire into
`plugin_manager.py`. Add `PluginCoordinator.list_plugins()` method.

**11.1d Audit query endpoint** — `GET /admin/audit`. Wire into `audit.py`
`AuditLogger.query_events()`. Add pagination wrapper.

### 11.2 Dashboard Auth (dev-merger, ~2 tasks)

**11.2a Login endpoint** — `POST /api/v1/auth/login`. Parse
`AGORA_DASHBOARD_USERS`, bcrypt verify, issue JWT via `TokenManager`.

**11.2b Dashboard WS auth** — `/ws/dashboard` endpoint. Validate JWT from
query param, upgrade, handle subscribe/unsubscribe messages.

### 11.3 Dashboard Frontend Core (dev-merger, ~3 tasks)

**11.3a HTML shell + CSS** — Rewrite `dashboard.html`: login overlay, 6-tab
nav, page containers. Extract CSS to `dashboard.css`. Dark theme, responsive.

**11.3b JS core modules** — `app.js` (router, auth state, nav), `api.js`
(fetch with JWT), `ws-client.js` (connect, reconnect, subscribe).

**11.3c Overview + Discussions pages** — Port existing overview logic to
`pages/overview.js`. Build real-time discussion viewer in
`pages/discussions.js` with WS subscription.

### 11.4 Dashboard Feature Pages (dev-merger, ~3 tasks)

**11.4a Task kanban page** — `pages/tasks.js` + `components/kanban-board.js`.
Fetch task graphs, render kanban columns, real-time card movement via WS.

**11.4b Agent management page** — `pages/agents.js`. Agent table with
approve/reject/suspend actions, inline TPM/concurrency edit, token rotation.

**11.4c Plugin + Audit pages** — `pages/plugins.js` (plugin list, enable/disable,
health) + `pages/audit.js` (filterable table, pagination).

### 11.5 Integration + Polish (dev-merger, ~1 task)

**11.5a Integration wiring** — All routers registered in `main.py`, dashboard
WS connected to event bus, backward compat tested (no `AGORA_DASHBOARD_USERS`).

## Files Summary

| Phase | New Files | Modified Files | DB Changes |
|---|---|---|---|
| 11.1 Backend | — | router.py, dashboard.py, models.py, plugin_manager.py | — |
| 11.2 Auth | — | main.py, ws_handlers.py, models.py | — |
| 11.3 Frontend Core | dashboard.html, dashboard.css, app.js, api.js, ws-client.js, pages/overview.js, pages/discussions.js | — | — |
| 11.4 Feature Pages | pages/tasks.js, pages/agents.js, pages/plugins.js, pages/audit.js, components/kanban-board.js, components/event-feed.js, components/modal.js | — | — |
| 11.5 Integration | — | main.py | — |

## Estimated Effort

| Part | Complexity | Dev Tasks | Review Tasks | Total Effort |
|---|---|---|---|---|
| 11.1 Backend API | Low | ~4 | ~1 | 2-3 days |
| 11.2 Auth | Medium | ~2 | ~1 | 1-2 days |
| 11.3 Frontend Core | Medium | ~3 | ~1 | 2-3 days |
| 11.4 Feature Pages | Medium | ~3 | ~1 | 2-3 days |
| 11.5 Integration | Low | ~1 | ~1 | 1 day |
| **Total** | — | **~13** | **~5** | **8-12 days** |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| ES modules not supported in some browsers | Low | All modern browsers support; dashboard is ops tool, not consumer |
| WS connection drops during long sessions | Medium | Auto-reconnect with exponential backoff in ws-client.js |
| Large audit logs slow query | Low | Pagination + SQLite indexes on timestamp, event_type |
| bcrypt optional dependency missing | Low | Fall back to plain-text compare with warning log if bcrypt not installed |
| Chart.js CDN unavailable (air-gapped) | Low | Document fallback: download chart.js to static/vendor/ |
