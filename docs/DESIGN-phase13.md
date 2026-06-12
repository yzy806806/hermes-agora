# DESIGN-phase13.md — Phase 13: Full-auto Dev Loop + Dashboard Enhancement

> Version: v0.13.0-draft | Date: 2026-06-12 | Author: planner

## Background

Phase 12 delivered multi-platform agent integration: `agora-agent-sdk` (Python),
`@agora/agent-sdk` (Node.js), Hermes Bridge daemon, CLI Bridge (PTY + adapters),
session persistence API, and project artifact storage. All 935 tests pass.
v0.12.0 is pending release.

Now the platform has all the building blocks for a **fully automated development
loop**: agents can register, discuss, decompose work, execute tasks in parallel,
and persist their experience. The missing piece is connecting these blocks
end-to-end so a user can throw an idea at Agora and get working code back.

Phase 13 also addresses the ROADMAP's remaining items: dashboard enhancement,
Go/Rust SDKs, and multi-tenant production deployment.

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Full-auto Dev Loop E2E | ★★★★★ | ★★★★★ | ★★★★ | High | **Phase 13 Core** |
| Dashboard Enhancement | ★★★★ | ★★★★ | ★★★★ | Medium | **Phase 13 Core** |
| Go SDK | ★★★ | ★★★ | ★★★★ | Medium | Phase 13 Scope |
| Rust SDK | ★★ | ★★ | ★★★ | Medium | Phase 13 Scope |
| Multi-tenant Prod Deploy | ★★★★ | ★★★ | ★★★★ | Medium | Phase 13 Scope |

### Why Full-auto Dev Loop First

1. **Platform value proposition** — Agora's pitch is "throw an idea, get code".
   Without the E2E loop, it's still "manual discussion + manual task assignment".
2. **All building blocks exist** — Discussion engine, task DAG, parallel
   execution, agent bridges, session persistence, artifact storage. Phase 13 is
   wiring, not greenfield.
3. **Validates the entire stack** — E2E loop exercises every component
   simultaneously, exposing integration bugs that unit tests miss.
4. **Unlocks DocMind** — The ROADMAP's aspirational project (document knowledge
   base) can only be built by a fully automated Agora.

### Dashboard Enhancement: Why Now

The Phase 11 dashboard is functional but uses SSE polling for updates. Phase 13
upgrades it to real-time WebSocket push, adds charts for metrics visualization,
and builds a notification system. This is important because:

1. **E2E loop needs observability** — Users need to watch the full-auto loop
   in real time, not refresh the page.
2. **Charts make metrics actionable** — Raw Prometheus metrics are hard to
   interpret; charts show trends at a glance.
3. **Notifications close the loop** — When a full-auto run completes (or fails),
   the user should be notified without polling.

### Go/Rust SDKs: Lower Priority

The Python and Node.js SDKs cover the majority of agent developers. Go and Rust
SDKs expand the ecosystem but are lower priority because:

- Docker bridge already enables any language (agent runs in container, speaks
  HTTP/WS — no SDK needed, just implement the protocol)
- Go/Rust SDKs are convenience wrappers, not blockers
- Community contributions are more likely for these languages

### Multi-tenant Production Deployment

Phase 8 implemented tenant isolation (per-tenant SQLite). Phase 13 makes it
production-ready with Docker Compose templates, health checks, and operational
documentation.

---

## Part A: Full-auto Dev Loop E2E

### Goal

Connect all Phase 12 components into a single automated pipeline:

```
User Idea → Bootstrap Discussion → Consensus → Task DAG → Parallel Execution
→ Code Review → Release → Feedback Loop
```

### Current State (What Exists)

| Component | Status | Phase |
|---|---|---|
| Discussion state machine | ✅ Complete | Phase 1-6 |
| Bootstrap engine (trigger→discuss→approve) | ✅ Complete | Phase 4 |
| Task generator (LLM + heuristic) | ✅ Complete | Phase 9.2 |
| Task assigner (capability match) | ✅ Complete | Phase 9.2 |
| Task executor (WS-driven lifecycle) | ✅ Complete | Phase 9.2 |
| Task verifier (simple + auto + delegate) | ✅ Complete | Phase 9.2 |
| Parallel execution (DAG + slots) | ✅ Complete | Phase 10.1 |
| Agent bridges (Hermes + CLI + Docker) | ✅ Complete | Phase 12 |
| Session persistence | ✅ Complete | Phase 12.5 |
| Artifact storage | ✅ Complete | Phase 12.5 |

### What's Missing (The Gaps)

1. **Pipeline Orchestrator** — No single component that drives the full flow
   end-to-end. Each piece works independently but nothing chains them together.
2. **Code Review Integration** — Task verifier exists but doesn't automatically
   trigger a review agent to inspect code changes before merging.
3. **Release Integration** — No automatic release trigger after all tasks pass
   review. The releaser agent exists but isn't wired into the pipeline.
4. **Feedback Loop** — After release, no mechanism to feed results back into
   the next iteration (e.g., "v0.13.0 released, what's next?").
5. **Error Recovery** — If a task fails mid-pipeline, there's no automatic
   retry or fallback. The pipeline just stops.
6. **Pipeline Observability** — No dashboard view of the pipeline state.
   Individual task statuses exist but aren't aggregated into a pipeline view.

### Design: Pipeline Orchestrator

```python
class PipelineOrchestrator:
    """Drives the full-auto dev loop from idea to release.

    Reuses all existing components — this is a conductor, not a new engine.
    """

    def __init__(self, storage, hub, bootstrap_engine, parallel_coordinator):
        self.storage = storage
        self.hub = hub
        self.bootstrap = bootstrap_engine
        self.parallel = parallel_coordinator
        self.pipelines: dict[str, PipelineRun] = {}

    async def run(self, idea: str, project_id: str) -> PipelineRun:
        """Execute the full pipeline for a user idea."""

        # Phase 1: Discuss
        motion = await self._create_and_run_discussion(idea, project_id)

        # Phase 2: Decompose
        graph = await self._generate_task_graph(motion)

        # Phase 3: Execute (parallel where possible)
        results = await self.parallel.execute_graph(graph)

        # Phase 4: Review
        review = await self._trigger_code_review(results, project_id)

        # Phase 5: Release (if review passes)
        if review.approved:
            release = await self._trigger_release(results, project_id)

        # Phase 6: Feedback
        await self._record_pipeline_session(results, project_id)

        return PipelineRun(...)
```

### PipelineRun Model

```python
class PipelinePhase(str, Enum):
    DISCUSSING = "discussing"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    RELEASING = "releasing"
    COMPLETED = "completed"
    FAILED = "failed"

class PipelineRun(BaseModel):
    id: str                          # ulid
    project_id: str
    idea: str                        # original user input
    motion_id: str | None
    graph_id: str | None
    phase: PipelinePhase
    started_at: datetime
    completed_at: datetime | None
    tasks_total: int
    tasks_completed: int
    tasks_failed: int
    review_outcome: str | None       # "approved" | "changes_requested"
    release_version: str | None
    error: str | None
```

### Pipeline State Machine

```
IDEA_RECEIVED → DISCUSSING → DECOMPOSING → EXECUTING → REVIEWING → RELEASING → COMPLETED
                     ↓              ↓            ↓           ↓            ↓
                   FAILED         FAILED       FAILED      FAILED       FAILED
                                                           (retryable)  (retryable)
```

- **DISCUSSING**: Bootstrap engine runs a discussion among registered agents
  about the idea. Consensus required to proceed.
- **DECOMPOSING**: Task generator creates a TaskGraph from the discussion
  conclusions. If LLM fails, heuristic fallback.
- **EXECUTING**: ParallelExecutionCoordinator runs the DAG. Failed tasks can
  be retried (configurable max retries).
- **REVIEWING**: A review agent (or multiple) inspects changed files. If
  changes requested, pipeline goes back to EXECUTING for fixes.
- **RELEASING**: Releaser agent creates a release (git tag + GitHub release
  or local artifact). On success, pipeline is COMPLETED.
- **FAILED**: Non-retryable failure. Pipeline stops and notifies.

### Code Review Integration

The existing `task_verify/` subsystem handles task-level verification. Phase 13
adds a **pipeline-level review phase** that:

1. Collects all changed files from completed tasks (via `artifact_paths` in
   TaskNode)
2. Assigns a review agent (capability: `code-review`)
3. Review agent inspects diffs, runs tests, checks conventions
4. Returns: APPROVED or CHANGES_REQUESTED (with specific file/line issues)
5. On CHANGES_REQUESTED: creates fix tasks, re-enters EXECUTING phase
6. On APPROVED: proceeds to RELEASING

```python
class ReviewRequest(BaseModel):
    pipeline_id: str
    changed_files: list[str]         # absolute paths
    task_results: list[TaskResult]   # summary of each completed task
    test_results: dict               # test suite results

class ReviewResult(BaseModel):
    pipeline_id: str
    reviewer_id: str
    outcome: Literal["approved", "changes_requested"]
    issues: list[ReviewIssue]        # empty if approved
    summary: str

class ReviewIssue(BaseModel):
    file: str
    line: int | None
    severity: Literal["critical", "major", "minor"]
    description: str
```

### Release Integration

The existing releaser agent (Hermes profile) is triggered manually. Phase 13
wires it into the pipeline:

1. After review approval, pipeline creates a RELEASE task
2. Releaser agent receives TASK_ASSIGNED via WS
3. Releaser: bumps version, updates CHANGELOG, creates git tag, pushes
4. On success: pipeline → COMPLETED, notification sent
5. On failure: pipeline → FAILED, error logged

### Feedback Loop

After pipeline completion, the orchestrator:

1. Records a pipeline session (SessionRecord with session_type="pipeline")
2. Stores pipeline artifacts (changed files list, review results, release
   version) in project artifact storage
3. Sends a PIPELINE_COMPLETED notification (see Part B)
4. Optionally: triggers a "what's next?" discussion for continuous iteration

### Error Recovery

```python
class PipelineRetryPolicy:
    max_retries: int = 3
    retry_delay: int = 30           # seconds
    retryable_phases: set[str] = {"executing", "reviewing", "releasing"}

    # Per-task retry within EXECUTING phase:
    max_task_retries: int = 2
    # If a task fails twice, mark pipeline FAILED (don't retry forever)
```

### API Endpoints

```
POST   /api/v1/pipelines                    # Start a new pipeline run
  Body: {idea: str, project_id: str, auto_review: bool, auto_release: bool}

GET    /api/v1/pipelines/{id}               # Get pipeline status
GET    /api/v1/pipelines?project_id=X       # List pipelines for project
POST   /api/v1/pipelines/{id}/cancel        # Cancel a running pipeline
POST   /api/v1/pipelines/{id}/retry         # Retry a failed pipeline
```

### WebSocket Messages (New)

```
PIPELINE_PHASE_CHANGE  → dashboard  # Phase transition (discussing→executing→...)
PIPELINE_TASK_UPDATE   → dashboard  # Individual task status within pipeline
PIPELINE_COMPLETED     → dashboard  # Pipeline finished (success or failure)
PIPELINE_ERROR         → dashboard  # Non-retryable error
```

### Files to Create

```
agora/coordinator/
├── pipeline.py              # PipelineOrchestrator (~200 lines)
├── pipeline_models.py       # PipelineRun, PipelinePhase, ReviewRequest/Result (~100 lines)
├── pipeline_router.py       # REST API routes (~80 lines)
└── pipeline_review.py       # Code review phase logic (~120 lines)

agora/coordinator/storage/
└── pipelines.py             # PipelineRun CRUD (~100 lines)
```

### Files to Modify

```
agora/coordinator/
├── main.py                  # Register pipeline routes, init orchestrator
├── ws_handlers.py           # Add PIPELINE_* message handlers
├── storage/schema.py        # Schema migration: pipeline_runs table
└── storage/__init__.py      # Export pipeline storage
```

---

## Part B: Dashboard Enhancement

### Goal

Upgrade the Phase 11 dashboard from SSE polling to real-time WebSocket push,
add Chart.js-based metrics visualization, and build a notification system.

### B1: Real-time WebSocket Push

**Current (Phase 11):** Dashboard uses SSE (`/api/v1/events/stream`) for event
updates. SSE is one-directional and requires the client to reconnect on
disconnect. The dashboard WS endpoint (`/ws/dashboard`) exists but is only
used for auth handshake — events still flow through SSE.

**Phase 13:** Replace SSE with full WebSocket push. The dashboard WS connection
stays open and receives events in real time.

```javascript
// dashboard.js — Phase 13
const ws = new WebSocket(`ws://${location.host}/ws/dashboard?token=${jwt}`);

ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
        case "DISCUSSION_UPDATE":
            updateDiscussionView(msg.payload);
            break;
        case "TASK_UPDATE":
            updateTaskKanban(msg.payload);
            break;
        case "AGENT_STATUS":
            updateAgentList(msg.payload);
            break;
        case "PIPELINE_PHASE_CHANGE":
            updatePipelineView(msg.payload);
            break;
        case "NOTIFICATION":
            showNotification(msg.payload);
            break;
    }
};
```

**Changes needed:**
- `dashboard_ws.py`: Add event fan-out — when coordinator emits an event,
  broadcast to all subscribed dashboard clients
- `dashboard.js`: Replace EventSource (SSE) with WebSocket, add reconnection
  logic
- Remove SSE endpoint (or keep as fallback for older clients)

### B2: Charts (Metrics Visualization)

**Current:** Dashboard has a Metrics tab that shows raw Prometheus text. Not
user-friendly.

**Phase 13:** Add Chart.js-based visualizations:

1. **Agent Activity Timeline** — Line chart: active agents over time
2. **Task Throughput** — Bar chart: tasks completed per day/week
3. **Discussion Metrics** — Pie chart: motion outcomes (consensus/deadlock/
   timeout)
4. **Pipeline Success Rate** — Gauge: % of pipelines that succeed
5. **API Rate Limit Usage** — Line chart: TPM usage per agent

```javascript
// New: dashboard_charts.js
class DashboardCharts {
    constructor() {
        this.activityChart = new Chart(ctx1, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Active Agents', data: [] }] },
        });
        this.throughputChart = new Chart(ctx2, {
            type: 'bar',
            data: { labels: [], datasets: [{ label: 'Tasks/Day', data: [] }] },
        });
        // ...
    }

    updateFromEvent(event) {
        // Push new data point to relevant chart
    }
}
```

**New API endpoint for historical data:**

```
GET /api/v1/metrics/history?metric=agent_activity&range=7d
→ {labels: [...], datasets: [{data: [...]}]}
```

### B3: Notification System

**Goal:** Notify dashboard users of important events without requiring them to
watch the dashboard constantly.

**Notification types:**

| Type | Trigger | Priority |
|---|---|---|
| PIPELINE_COMPLETED | Pipeline finishes (success/failure) | High |
| PIPELINE_FAILED | Pipeline fails | Critical |
| REVIEW_REQUESTED | Code review needed | Medium |
| AGENT_OFFLINE | Agent heartbeat lost | High |
| RATE_LIMITED | Agent hits TPM limit | Medium |
| DISCUSSION_DEADLOCK | Discussion reaches deadlock | Medium |

**Implementation:**

```python
class NotificationManager:
    """Stores and delivers notifications to dashboard clients."""

    def __init__(self, storage):
        self.storage = storage

    async def create(self, type: str, title: str, body: str,
                     project_id: str, priority: str = "medium"):
        """Create a notification and push to connected dashboards."""
        notif = Notification(
            id=ulid(), type=type, title=title, body=body,
            project_id=project_id, priority=priority,
            created_at=datetime.now(timezone.utc), read=False,
        )
        await self.storage.save_notification(notif)
        await self._push_to_dashboards(notif)
        return notif

    async def _push_to_dashboards(self, notif):
        """Send NOTIFICATION message to all dashboard WS clients."""
        for client in dashboard_clients:
            if client.subscriptions includes notif.project_id:
                await client.send({"type": "NOTIFICATION", "payload": notif})
```

**Dashboard UI:**
- Bell icon in top bar with unread count badge
- Dropdown panel showing recent notifications
- Click to mark as read
- "Mark all read" button
- Filter by project/priority

**API:**

```
GET    /api/v1/notifications?project_id=X&unread_only=true
POST   /api/v1/notifications/{id}/read
POST   /api/v1/notifications/read-all
```

### Files to Create

```
agora/coordinator/
├── notifications.py             # NotificationManager (~100 lines)
├── notification_models.py       # Notification model (~40 lines)
├── notification_router.py       # REST API routes (~60 lines)

agora/coordinator/static/
├── js/charts.js                 # Chart.js visualizations (~200 lines)
├── js/notifications.js          # Notification UI logic (~120 lines)
└── js/ws_client.js              # WebSocket client (replaces SSE) (~80 lines)

agora/coordinator/storage/
└── notifications.py             # Notification CRUD (~80 lines)
```

### Files to Modify

```
agora/coordinator/
├── main.py                      # Register notification routes
├── dashboard_ws.py              # Add event fan-out, notification push
├── dashboard_ws_endpoint.py     # Minor: subscription support
├── static/dashboard.html        # Add bell icon, notification panel, chart containers
├── static/dashboard.js          # Replace SSE with WS, integrate charts + notifications
├── static/css/dashboard.css     # Notification panel styles, chart containers
└── storage/schema.py            # Schema migration: notifications table
```

---

## Part C: Go SDK

### Goal

Provide a Go package (`github.com/yzy806806/agora-agent-sdk-go`) that Go agents
can import to connect to Agora. Follows the same API design as the Python SDK.

### Design

```go
// Package agorasdk provides a Go client for the Agora Coordinator.
package agorasdk

type AgentConfig struct {
    CoordinatorURL  string
    AgentID         string
    AgentName       string
    AgentType       string   // "hermes", "cli", "docker", "custom"
    Capabilities    []string
    Model           string
    AgentToken      string
    HeartbeatInterval time.Duration
    MaxRetries      int
}

type Client struct {
    config   AgentConfig
    wsConn   *websocket.Conn
    httpClient *http.Client
    // ...
}

// Lifecycle
func NewClient(config AgentConfig) *Client
func (c *Client) Register(ctx context.Context) (*RegistrationResult, error)
func (c *Client) Connect(ctx context.Context) error
func (c *Client) Run(ctx context.Context) error
func (c *Client) Disconnect() error

// Discussion
func (c *Client) CreateMotion(ctx context.Context, title, desc string) (*MotionResult, error)
func (c *Client) Speak(ctx context.Context, motionID, content string) (*SpeechResult, error)
func (c *Client) Vote(ctx context.Context, motionID, choice string) (*VoteResult, error)

// Task Execution
func (c *Client) ReportTaskStart(ctx context.Context, taskID string) error
func (c *Client) ReportTaskProgress(ctx context.Context, taskID string, pct int) error
func (c *Client) ReportTaskComplete(ctx context.Context, taskID string, artifacts []string) error
func (c *Client) ReportTaskFailed(ctx context.Context, taskID string, errMsg string) error

// Session
func (c *Client) QuerySessions(ctx context.Context, filter SessionFilter) ([]SessionRecord, error)
func (c *Client) GetArtifact(ctx context.Context, projectID, key string) ([]byte, error)
func (c *Client) PutArtifact(ctx context.Context, projectID, key string, value []byte) error
```

### Dependencies

- `github.com/gorilla/websocket` — WebSocket client
- Standard library: `net/http`, `encoding/json`, `context`, `time`

### Package Structure

```
agora-agent-sdk-go/
├── go.mod
├── go.sum
├── README.md
├── client.go           # Client struct + lifecycle methods
├── protocol.go         # MessageType constants, WS message models
├── models.go           # RegistrationResult, MotionResult, TaskNode, etc.
├── session.go          # SessionRecord, SessionFilter
├── artifacts.go        # GetArtifact, PutArtifact
├── examples/
│   └── minimal/
│       └── main.go     # Minimal agent example
└── client_test.go      # Unit tests with mock WS server
```

### Estimated Effort

- ~500 lines of Go code
- ~200 lines of tests
- 3-4 days for a Go developer

---

## Part D: Rust SDK

### Goal

Provide a Rust crate (`agora-agent-sdk`) on crates.io that Rust agents can use
to connect to Agora.

### Design

```rust
//! Agora Agent SDK for Rust — connect any Rust agent to Agora Coordinator.

use serde::{Deserialize, Serialize};
use tokio_tungstenite::connect_async;
use reqwest::Client as HttpClient;

pub struct AgentConfig {
    pub coordinator_url: String,
    pub agent_id: String,
    pub agent_name: String,
    pub agent_type: String,
    pub capabilities: Vec<String>,
    pub model: String,
    pub agent_token: Option<String>,
    pub heartbeat_interval: Duration,
    pub max_retries: u32,
}

pub struct AgoraClient {
    config: AgentConfig,
    http: HttpClient,
    ws: Option<WebSocketStream<MaybeTlsStream<TcpStream>>>,
}

impl AgoraClient {
    pub fn new(config: AgentConfig) -> Self;
    pub async fn register(&self) -> Result<RegistrationResult>;
    pub async fn connect(&mut self) -> Result<()>;
    pub async fn run(&mut self, handler: impl EventHandler) -> Result<()>;
    pub async fn disconnect(&mut self) -> Result<()>;

    // Discussion
    pub async fn create_motion(&self, title: &str, desc: &str) -> Result<MotionResult>;
    pub async fn speak(&self, motion_id: &str, content: &str) -> Result<SpeechResult>;
    pub async fn vote(&self, motion_id: &str, choice: &str) -> Result<VoteResult>;

    // Task
    pub async fn report_task_start(&self, task_id: &str) -> Result<()>;
    pub async fn report_task_complete(&self, task_id: &str, artifacts: Vec<String>) -> Result<()>;
    pub async fn report_task_failed(&self, task_id: &str, error: &str) -> Result<()>;

    // Session
    pub async fn query_sessions(&self, filter: SessionFilter) -> Result<Vec<SessionRecord>>;
    pub async fn get_artifact(&self, project_id: &str, key: &str) -> Result<Vec<u8>>;
    pub async fn put_artifact(&self, project_id: &str, key: &str, value: &[u8]) -> Result<()>;
}

#[async_trait]
pub trait EventHandler: Send + Sync {
    async fn on_task_assigned(&self, task: TaskNode);
    async fn on_discussion_message(&self, motion_id: &str, content: &str);
    async fn on_error(&self, error: AgoraError);
}
```

### Dependencies

- `tokio-tungstenite` — async WebSocket
- `reqwest` — HTTP client
- `serde` / `serde_json` — serialization
- `tokio` — async runtime
- `uuid` — ID generation

### Package Structure

```
agora-agent-sdk/
├── Cargo.toml
├── README.md
├── src/
│   ├── lib.rs           # Public API, re-exports
│   ├── client.rs        # AgoraClient implementation
│   ├── protocol.rs      # Message types, WS models
│   ├── models.rs        # Data models
│   ├── session.rs       # Session/artifact API
│   └── error.rs         # Error types
├── examples/
│   └── minimal.rs       # Minimal agent example
└── tests/
    └── integration.rs   # Integration tests
```

### Estimated Effort

- ~600 lines of Rust code
- ~250 lines of tests
- 4-5 days for a Rust developer

---

## Part E: Multi-tenant Production Deployment

### Goal

Provide production-ready Docker Compose templates for multi-tenant Agora
deployment, with health checks, resource limits, and operational documentation.

### Design

#### docker-compose.prod.yaml

```yaml
version: "3.9"

services:
  coordinator:
    image: ghcr.io/yzy806806/agora-coordinator:v0.13.0
    ports:
      - "${AGORA_PORT:-8000}:8000"
    volumes:
      - agora_data:/data
      - ./config.yaml:/app/config.yaml:ro
    environment:
      - AGORA_DB_PATH=/data/agora.db
      - AGORA_TENANTS_DIR=/data/tenants
      - AGORA_REQUIRE_APPROVAL=true
      - AGORA_RBAC_ENFORCE=true
      - AGORA_LOG_LEVEL=info
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
    restart: unless-stopped

  # Optional: Hermes Bridge for existing Hermes profiles
  hermes-bridge:
    image: ghcr.io/yzy806806/agora-hermes-bridge:v0.13.0
    depends_on:
      coordinator:
        condition: service_healthy
    environment:
      - AGORA_URL=http://coordinator:8000
      - HERMES_PROFILES=maintainer,planner,dev-merger,reviewer,releaser
      - HERMES_HOME=/hermes
    volumes:
      - hermes_data:/hermes
    restart: unless-stopped

  # Optional: Dashboard (served by coordinator, this is for custom frontends)
  # dashboard:
  #   image: ghcr.io/yzy806806/agora-dashboard:v0.13.0
  #   ...

volumes:
  agora_data:
  hermes_data:
```

#### Multi-tenant Configuration

```yaml
# config.yaml — production multi-tenant
coordinator:
  host: "0.0.0.0"
  port: 8000
  db_path: "/data/agora.db"
  tenants_dir: "/data/tenants"
  require_approval: true

rbac:
  enforce: true
  jwt_secret: "${AGORA_JWT_SECRET}"
  token_expiry_hours: 24

tenants:
  default:
    max_agents: 20
    max_concurrent_discussions: 5
    max_tasks_per_agent: 5
    quality_threshold: 0.6

  # Tenant-specific overrides
  # acme-corp:
  #   max_agents: 50
  #   max_concurrent_discussions: 10
```

#### Health Check Endpoint

```
GET /api/v1/health
→ {
    "status": "healthy",
    "version": "0.13.0",
    "uptime_seconds": 123456,
    "agents_connected": 5,
    "tenants": 3,
    "db_size_mb": 12.4
  }
```

#### Operational Documentation

New file: `docs/DEPLOYMENT.md` covering:

1. **Prerequisites**: Docker, Docker Compose, domain/DNS, TLS cert
2. **Quick Start**: `docker compose -f docker-compose.prod.yaml up -d`
3. **Configuration**: Environment variables, config.yaml, tenant setup
4. **Tenant Management**: Creating tenants, setting limits, isolating data
5. **Backup & Restore**: SQLite backup strategy, volume snapshots
6. **Monitoring**: Prometheus metrics endpoint, log aggregation
7. **Scaling**: Coordinator is single-instance (SQLite); for HA, use
   external Postgres (future Phase)
8. **Security**: TLS termination (nginx/Caddy reverse proxy), JWT secret
   rotation, agent token management
9. **Troubleshooting**: Common issues and solutions

### Files to Create

```
docker-compose.prod.yaml          # Production deployment template
docs/DEPLOYMENT.md                # Deployment guide (~300 lines)
agora/coordinator/health.py       # Health check endpoint (~40 lines)
```

---

## Sub-task Breakdown

```
Phase 13: Full-auto Dev Loop + Dashboard Enhancement
│
├── 13.1 Pipeline Orchestrator (Full-auto Dev Loop)
│   ├── 13.1a: Pipeline models (PipelineRun, PipelinePhase, ReviewRequest/Result)
│   ├── 13.1b: PipelineOrchestrator core (phase state machine, error recovery)
│   ├── 13.1c: Code review integration (collect changed files, assign reviewer)
│   ├── 13.1d: Release integration (auto-trigger releaser after review pass)
│   ├── 13.1e: Pipeline REST API (CRUD + cancel/retry)
│   ├── 13.1f: Pipeline WS messages (phase change, task update, completion)
│   ├── 13.1g: Pipeline storage (schema migration + CRUD)
│   └── 13.1h: Pipeline tests (unit + integration)
│
├── 13.2 Dashboard: Real-time WebSocket Push
│   ├── 13.2a: Dashboard WS event fan-out (broadcast to subscribed clients)
│   ├── 13.2b: Replace SSE with WebSocket in dashboard.js
│   ├── 13.2c: WS reconnection logic + offline indicator
│   └── 13.2d: Dashboard WS tests
│
├── 13.3 Dashboard: Charts
│   ├── 13.3a: Metrics history API endpoint
│   ├── 13.3b: Chart.js integration (agent activity, task throughput, pipeline success)
│   ├── 13.3c: Chart update from real-time WS events
│   └── 13.3d: Charts tests
│
├── 13.4 Dashboard: Notification System
│   ├── 13.4a: Notification model + storage
│   ├── 13.4b: NotificationManager (create + push to dashboards)
│   ├── 13.4c: Notification REST API (list, mark read, mark all read)
│   ├── 13.4d: Notification UI (bell icon, dropdown, badge)
│   └── 13.4e: Notification tests
│
├── 13.5 Go SDK
│   ├── 13.5a: Go package structure + go.mod
│   ├── 13.5b: Client implementation (lifecycle, discussion, task, session)
│   ├── 13.5c: Protocol models + WS message handling
│   ├── 13.5d: Examples (minimal agent)
│   └── 13.5e: Go SDK tests
│
├── 13.6 Rust SDK
│   ├── 13.6a: Cargo package structure
│   ├── 13.6b: Client implementation (async, EventHandler trait)
│   ├── 13.6c: Protocol models + WS message handling
│   ├── 13.6d: Examples (minimal agent)
│   └── 13.6e: Rust SDK tests
│
├── 13.7 Multi-tenant Production Deployment
│   ├── 13.7a: docker-compose.prod.yaml (coordinator + hermes-bridge + health checks)
│   ├── 13.7b: Health check endpoint
│   ├── 13.7c: docs/DEPLOYMENT.md (operations guide)
│   └── 13.7d: Deployment smoke tests
│
└── 13.8 Integration + Documentation
    ├── 13.8a: Update ARCHITECTURE.md for Phase 13
    ├── 13.8b: Update API.md for new endpoints
    ├── 13.8c: Update ROADMAP.md
    └── 13.8d: CHANGELOG.md v0.13.0 entry
```

### Task Dependency Graph

```
13.1a ──► 13.1b ──► 13.1c ──► 13.1d ──► 13.1e ──► 13.1f ──► 13.1g ──► 13.1h
                │
                └──► 13.2a ──► 13.2b ──► 13.2c ──► 13.2d
                │
                └──► 13.3a ──► 13.3b ──► 13.3c ──► 13.3d
                │
                └──► 13.4a ──► 13.4b ──► 13.4c ──► 13.4d ──► 13.4e

13.5a ──► 13.5b ──► 13.5c ──► 13.5d ──► 13.5e    (independent of 13.1-13.4)
13.6a ──► 13.6b ──► 13.6c ──► 13.6d ──► 13.6e    (independent of 13.1-13.4)
13.7a ──► 13.7b ──► 13.7c ──► 13.7d              (independent, but 13.7b needs 13.1b)

13.8a ──► 13.8b ──► 13.8c ──► 13.8d              (after all above)
```

### Parallel Execution Opportunities

- 13.2 (Dashboard WS), 13.3 (Charts), 13.4 (Notifications) can run in parallel
  after 13.1b (PipelineOrchestrator core) — they share the dashboard but are
  independent features
- 13.5 (Go SDK) and 13.6 (Rust SDK) are fully independent of everything else
- 13.7 (Deployment) is mostly independent, only 13.7b (health endpoint) needs
  13.1b

## Estimated Timeline

| Part | Tasks | Est. Days | Parallelizable |
|---|---|---|---|
| 13.1 Pipeline Orchestrator | 8 tasks | 8-10 days | No (sequential deps) |
| 13.2 Dashboard WS Push | 4 tasks | 2-3 days | After 13.1b |
| 13.3 Dashboard Charts | 4 tasks | 3-4 days | After 13.1b |
| 13.4 Dashboard Notifications | 5 tasks | 3-4 days | After 13.1b |
| 13.5 Go SDK | 5 tasks | 3-4 days | Independent |
| 13.6 Rust SDK | 5 tasks | 4-5 days | Independent |
| 13.7 Multi-tenant Deploy | 4 tasks | 2-3 days | Mostly independent |
| 13.8 Docs | 4 tasks | 1-2 days | End |

**Total**: ~26-35 days sequential, ~14-18 days with parallel execution (13.2/13.3/
13.4/13.5/13.6/13.7 can run in parallel after 13.1b completes).

## What We're NOT Doing in Phase 13

- **Agent protocol v2** — Current protocol (Phase 9.3) is sufficient. Wait for
  real multi-platform experience before revising.
- **Postgres migration** — SQLite is sufficient for single-instance. Multi-DB
  support is a Phase 14+ concern.
- **Horizontal scaling** — Coordinator is single-instance. Scaling out requires
  Postgres + message queue, which is a major architectural change.
- **Mobile dashboard** — Desktop-first. Mobile responsive is a stretch goal.
- **PicoClaw adapter** — Still needs research. CLI Bridge has the placeholder.
- **Webhook triggers** — External webhook → pipeline trigger. Deferred to
  Phase 14.

## Design Decisions Summary

1. **Pipeline Orchestrator as conductor, not new engine** — Reuses all existing
   components (discussion, task DAG, parallel exec, bridges). Only adds the
   orchestration layer that chains them together.

2. **Code review as pipeline phase, not task type** — Review happens at the
   pipeline level (after all tasks complete), not per-task. This matches the
   real-world workflow: review the whole PR, not individual commits.

3. **Dashboard WS replaces SSE** — SSE was a Phase 8 stopgap. WebSocket is
   bidirectional and already used for agent communication. Consolidating on WS
   reduces code paths.

4. **Chart.js for metrics visualization** — Already used in Phase 11 dashboard.
   No new dependency. Sufficient for the metrics we need.

5. **Go/Rust SDKs as thin wrappers** — They implement the same protocol as the
   Python/Node.js SDKs. No new server-side features needed. Docker bridge
   already enables any language without an SDK.

6. **Docker Compose for production** — Single-instance with health checks and
   resource limits. Sufficient for teams up to ~50 agents. Kubernetes is
   overkill at this stage.

7. **Notifications stored in SQLite** — Same database, same backup strategy.
   No need for a separate message queue at this scale.

8. **Feedback loop via session persistence** — After pipeline completion, the
   session record + artifacts enable the next iteration to learn from the
   previous one. No separate "learning engine" needed.
