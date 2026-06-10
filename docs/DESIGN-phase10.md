# DESIGN-phase10.md — Phase 10: Parallel Execution + RBAC + Plugin Ecosystem

> Version: v0.10.0-draft | Date: 2026-06-10 | Author: planner

## Background

Phase 9 delivered platform independence, a sequential task execution engine,
a standardized agent registration protocol, and per-agent API rate limiting.
Agora v0.9.3 can now connect agents, run discussions, generate task graphs,
and execute them—but only one at a time (sequential), with a single shared
admin token for all authorization, and no way to extend functionality.

Three major gaps remain before Agora can fulfill the ROADMAP vision of
"fully automatic project development":

1. **Parallel task execution** — The task graph already models DAG dependencies,
   but execution is sequential. Agents sit idle while one task runs, wasting
   the multi-agent architecture. Parallel execution is the key unlock for
   truly automated development pipelines.
2. **RBAC (Role-Based Access Control)** — Every API call is either public or
   behind a single `AGORA_ADMIN_TOKEN`. There's no concept of who can modify
   agent configs, approve registrations, delete tenants, or view dashboards.
   As Agora grows to production use, this is a security blocker.
3. **Plugin ecosystem** — Extensibility has been deferred since Phase 5.
   There's no way to add custom discussion policies, custom voting methods,
   custom task verifiers, or third-party integrations without modifying
   Agora core code.

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Parallel Task Execution | ★★★★★ | ★★★★★ | ★★★★ | High | **Phase 10 Core** |
| RBAC | ★★★★ | ★★★★ | ★★★★★ | Medium | **Phase 10 Core** |
| Plugin Ecosystem | ★★★★ | ★★★ | ★★★ | High | **Phase 10 Core** |
| Integration Testing | ★★★★ | ★★★ | ★★★★ | Medium | Phase 10 Follow |
| Performance Benchmarking | ★★★ | ★★ | ★★★★ | Low | Defer to Phase 11 |
| Agent Protocol v2 | ★★★ | ★★ | ★★ | Medium | Defer to Phase 11 |

### Why these three together

1. Parallel execution depends on RBAC — when multiple agents execute concurrently,
   we need to know their permissions to access files, modify resources, and
   interact with other agents.
2. RBAC enables plugins — plugins need controlled access to Agora internals;
   role-based permissions define what a plugin can and cannot do.
3. Plugins make RBAC extensible — custom permission checkers, custom role
   resolvers, and custom auth providers can be implemented as plugins.
4. All three are needed to graduate Agora from "dev tool" to "production platform."

### Parallel execution is the highest priority

The task graph (DAG) already exists from Phase 9.2. The missing piece is
the execution coordinator that understands which tasks can run concurrently
and manages resource conflicts. This is what enables "multiple agents working
simultaneously on different parts of a project."

## Architecture Target (end of Phase 10)

```
                        ┌─────────────────────────────────────────┐
                        │           Agora Platform v0.10           │
                        │  ┌──────────────────────────────────────┐ │
                        │  │         REST API + WebSocket Hub      │ │
                        │  └────────────────┬─────────────────────┘ │
                        │  ┌────────────────┴─────────────────────┐ │
                        │  │  ┌───────────┐ ┌──────────────────┐  │ │
                        │  │  │  RBAC     │ │  Parallel Task   │  │ │
                        │  │  │  Middle-  │ │  Execution       │  │ │
                        │  │  │  ware     │ │  Coordinator     │  │ │
                        │  │  └───────────┘ └──────────────────┘  │ │
                        │  │  ┌───────────┐ ┌──────────────────┐  │ │
                        │  │  │  Plugin   │ │  Discussion +    │  │ │
                        │  │  │  Manager  │ │  Task Engine     │  │ │
                        │  │  └───────────┘ └──────────────────┘  │ │
                        │  │  ┌───────────┐ ┌──────────────────┐  │ │
                        │  │  │  Agent    │ │  Storage         │  │ │
                        │  │  │  Registry │ │  (multi-tenant)  │  │ │
                        │  │  └───────────┘ └──────────────────┘  │ │
                        │  │  ┌──────────────────────────────┐    │ │
                        │  │  │  Plugin System (hooks +       │    │ │
                        │  │  │  lifecycle + sandbox)         │    │ │
                        │  │  └──────────────────────────────┘    │ │
                        │  └───────────────────────────────────────┘ │
                        └────────────────────┬──────────────────────┘
                                             │ HTTP/WS
                  ┌──────────────────────────┼──────────────────────────┐
                  ↓                          ↓                          ↓
             ┌─────────┐              ┌─────────┐              ┌─────────┐
             │ Hermes  │              │ Docker  │              │ Custom  │
             │ Agent   │              │ Agent   │              │ HTTP    │
             │ (role:  │              │ (role:  │              │ Agent   │
             │  coder) │              │  tester)│              │ (role:  │
             └─────────┘              └─────────┘              │  review)│
                                                               └─────────┘
```

## Part A: Parallel Task Execution

### A.1 Goal

Execute multiple independent tasks simultaneously across different agents,
while respecting DAG dependencies and resource constraints.

### A.2 Current State (Phase 9.2)

The Phase 9.2 task assigner (`task_assign.py`) processes tasks in BFS order:

```python
# assign_tasks() currently:
# 1. Sort tasks by dependency order
# 2. For each ready task, find a capable agent
# 3. Assign one task at a time (round-robin)
# 4. All assignments happen in one shot, then agent executes sequentially
```

Limitations:
- All tasks are assigned upfront, but execution is sequential per agent
- No concept of "execution slots" — an agent with `max_concurrent_tasks=3`
  receives 3 tasks but can only work on 1 at a time (no parallelism)
- No resource conflict detection — two agents might edit the same file

### A.3 Design: Parallel Execution Coordinator

New module: `agora/coordinator/task_parallel.py`

```python
class ParallelExecutionCoordinator:
    """Orchestrates parallel task execution across multiple agents.

    Responsibilities:
    1. Maintain a runqueue of ready tasks (deps satisfied)
    2. Track per-agent execution slots (respect max_concurrent_tasks)
    3. Detect resource conflicts (two tasks touching same file)
    4. Dynamically assign tasks as slots free up
    5. Handle task failures with partial rollback
    """

    def __init__(self, storage, hub, resource_tracker):
        self.runqueue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.agent_slots: dict[str, int] = {}  # agent_id → free slots
        self.resource_tracker: FileResourceTracker = resource_tracker
        self._running_futures: dict[str, asyncio.Task] = {}

    async def execute_graph(self, graph: TaskGraph) -> dict:
        """Execute all tasks in parallel where dependencies allow."""

    async def _on_task_complete(self, task_id: str):
        """When a task finishes, check if blocked tasks can now run."""

    async def _on_task_failed(self, task_id: str, error: str):
        """Handle failure: decide retry / abort dependent / continue."""
```

### A.4 Data Model Updates

**New: `ExecutionSlot`**

```python
class ExecutionSlot(BaseModel):
    """Tracks one concurrent execution slot."""
    task_id: str
    agent_id: str
    started_at: datetime
    status: str = "running"  # running | completing
```

**New: `ResourceLock`**

```python
class ResourceLock(BaseModel):
    """Tracks resource conflicts between parallel tasks."""
    resource_path: str          # e.g. "src/module.py"
    locked_by: str              # task_id holding the lock
    waiting_tasks: list[str]    # tasks waiting for this resource
    lock_type: str = "write"    # write | read
    acquired_at: datetime
```

**Updated: `TaskGraph` adds parallel metadata**

```python
class TaskGraph(BaseModel):
    id: str
    motion_id: str
    tasks: list[TaskNode]
    created_at: datetime
    # Phase 10 additions:
    parallel_mode: str = "auto"  # auto | sequential | parallel
    max_parallel_slots: int = 10  # global cap
    resource_conflict_policy: str = "warn"  # warn | abort | queue
```

### A.5 Resource Conflict Detection

New module: `agora/coordinator/task_resource.py`

```python
class FileResourceTracker:
    """Detects when two parallel tasks might conflict on filesystem resources.

    Strategy: Tasks declare expected file paths on assignment.
    Coordinator checks for overlaps and either:
    - Serializes conflicting tasks (one after another)
    - Allows read-sharing (multiple readers, single writer)
    - Warns and lets agents negotiate (for advanced use)
    """

    def __init__(self):
        self._locks: dict[str, ResourceLock] = {}

    def check_conflict(
        self, task_a: TaskNode, task_b: TaskNode
    ) -> bool:
        """Return True if tasks conflict on any file."""

    def acquire(
        self, task_id: str, paths: list[str], mode: str = "write"
    ) -> bool:
        """Try to acquire locks on file paths. Returns False if conflict."""

    def release(self, task_id: str) -> None:
        """Release all locks held by a task."""
```

### A.6 Parallel Execution Flow

```
Discussion closes → TaskGraph generated (existing Phase 9.2)
        │
        ▼
┌───────────────────────────────────────┐
│  Parallel Execution Coordinator        │
│                                        │
│  1. Load graph, resolve dependencies   │
│  2. Identify "ready" tasks (deps done) │
│  3. For each ready task:               │
│     a. Check agent slot availability   │
│     b. Check resource conflicts         │
│     c. Assign if both pass             │
│  4. Wait for task completion events    │
│  5. On complete: unlock resources,     │
│     re-evaluate readiness, repeat      │
│  6. On failure: decide retry/abort     │
│                                        │
│  WebSocket messages:                    │
│  TASK_ASSIGNED (existing)              │
│  TASK_STARTED  (new: agent confirms    │
│                 start of execution)     │
│  TASK_STATUS   (existing)              │
│  TASK_COMPLETED (existing)             │
│  TASK_FAILED   (existing)              │
│  TASK_BLOCKED  (new: blocked by        │
│                 resource conflict)      │
│  TASK_RETRY    (new: coordinator       │
│                 requests retry)         │
└───────────────────────────────────────┘
```

### A.7 New WebSocket Message Types

| Type | Direction | Payload | Description |
|---|---|---|---|
| `TASK_STARTED` | agent→coordinator | `{task_id, started_at}` | Agent confirms execution has begun |
| `TASK_BLOCKED` | coordinator→agent | `{task_id, reason, waiting_for}` | Task paused due to resource conflict |
| `TASK_UNBLOCKED` | coordinator→agent | `{task_id}` | Resource now available, resume |
| `TASK_RETRY` | coordinator→agent | `{task_id, reason, max_attempts}` | Re-execute failed task |
| `TASK_PROGRESS` | agent→coordinator | `{task_id, progress_pct, message}` | Optional progress updates |
| `GRAPH_COMPLETE` | coordinator→all | `{graph_id, summary}` | Entire task graph finished |

### A.8 Failure Handling in Parallel Mode

When a task fails in a parallel execution context:

1. **Isolate the failure** — Only dependent tasks are affected
2. **Retry policy**:
   - `retry: 0` (default) → dependent tasks blocked, wait for human
   - `retry: N` → retry up to N times with exponential backoff
   - `retry: -1` → retry indefinitely (for non-critical path tasks)
3. **Partial success** — Independent tasks continue running
4. **Rollback decisions** — Configurable per graph:
   - `abort-on-failure: false` → continue independent tasks
   - `abort-on-failure: true` → cancel all running tasks in graph

### A.9 Files to Create/Modify

| Area | Files | Action |
|---|---|---|
| Parallel coordinator | NEW: `agora/coordinator/task_parallel.py` | Core parallel execution logic |
| Resource tracking | NEW: `agora/coordinator/task_resource.py` | File conflict detection + locks |
| Data models | MODIFY: `agora/coordinator/task_models.py` | Add ResourceLock, ExecutionSlot, update TaskGraph |
| WS messages | MODIFY: `agora/coordinator/models.py` | Add TASK_STARTED, TASK_BLOCKED, etc. |
| WS handlers | MODIFY: `agora/coordinator/ws_handlers.py` | Handle new message types |
| Storage | MODIFY: `agora/coordinator/storage/schema.py` | Add execution_slots, resource_locks tables |
| Task exec | MODIFY: `agora/coordinator/task_exec.py` | Delegate to parallel coordinator |
| Task assign | MODIFY: `agora/coordinator/task_assign.py` | Support dynamic (re-)assignment |

### A.10 Bounded Scope (What Phase 10 does NOT do)

- **No distributed execution** — Multiple agents run on the same coordinator;
  multi-coordinator distributed task execution is Phase 12+
- **No streaming task output** — Agent sends results on completion, not
  incrementally (streaming is Phase 11+)
- **No priority preemption** — Running tasks aren't interrupted for higher
  priority tasks (preemption is Phase 11+)
- **No cross-graph parallelism** — Only tasks within one graph are parallelized;
  multiple graphs from different discussions are still sequential

## Part B: RBAC (Role-Based Access Control)

### B.1 Goal

Replace the single `AGORA_ADMIN_TOKEN` with a proper role-based authorization
system that controls who can do what across the Agora platform.

### B.2 Current State

Phase 9.3 authentication is minimal:
- Agent registration: `POST /register` with an `auth_token` field (not enforced)
- WS connection: `agent_token` validated on connect
- Admin endpoints: gated behind `AGORA_ADMIN_TOKEN` env var
- No per-endpoint permissions, no role hierarchy, no audit trail

### B.3 Design: RBAC Model

```python
class Role(str, Enum):
    """System roles with predefined permission sets."""
    SUPERADMIN = "superadmin"   # Full system access
    ADMIN = "admin"             # Tenant management, agent approval
    AGENT = "agent"             # Participate in discussions, execute tasks
    OBSERVER = "observer"       # Read-only: view discussions, metrics
    PLUGIN = "plugin"           # Limited: execute hooks, access plugin APIs

class Permission(str, Enum):
    """Granular permissions for RBAC."""
    # Agent management
    AGENT_REGISTER = "agent:register"
    AGENT_APPROVE = "agent:approve"
    AGENT_DELETE = "agent:delete"
    AGENT_CONFIG = "agent:config"

    # Discussion
    DISCUSSION_CREATE = "discussion:create"
    DISCUSSION_VIEW = "discussion:view"
    DISCUSSION_MODERATE = "discussion:moderate"

    # Task
    TASK_VIEW = "task:view"
    TASK_EXECUTE = "task:execute"
    TASK_ASSIGN = "task:assign"
    TASK_REVIEW = "task:review"

    # Tenant
    TENANT_CREATE = "tenant:create"
    TENANT_MANAGE = "tenant:manage"
    TENANT_DELETE = "tenant:delete"

    # System
    SYSTEM_CONFIG = "system:config"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_PLUGINS = "system:plugins"
    SYSTEM_AUDIT = "system:audit"

# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPERADMIN: set(Permission),  # All permissions
    Role.ADMIN: {
        Permission.AGENT_APPROVE, Permission.AGENT_CONFIG,
        Permission.AGENT_DELETE, Permission.DISCUSSION_MODERATE,
        Permission.TASK_VIEW, Permission.TASK_ASSIGN,
        Permission.TENANT_MANAGE, Permission.SYSTEM_METRICS,
        Permission.SYSTEM_CONFIG,
    },
    Role.AGENT: {
        Permission.AGENT_REGISTER, Permission.DISCUSSION_CREATE,
        Permission.DISCUSSION_VIEW, Permission.TASK_VIEW,
        Permission.TASK_EXECUTE, Permission.SYSTEM_METRICS,
    },
    Role.OBSERVER: {
        Permission.DISCUSSION_VIEW, Permission.TASK_VIEW,
        Permission.SYSTEM_METRICS,
    },
    Role.PLUGIN: {
        Permission.SYSTEM_PLUGINS,
    },
}
```

### B.4 RBAC Middleware

New module: `agora/coordinator/rbac.py`

```python
class RBACMiddleware:
    """FastAPI middleware that enforces RBAC on every request.

    Authentication:
    1. Extract token from Authorization header (Bearer <token>)
    2. Look up token → agent_id / user_id
    3. Resolve role(s) for that principal
    4. Check required permission for the endpoint

    Token types:
    - agent_token: from registration, identifies an agent
    - admin_token: from AGORA_ADMIN_TOKEN, identifies a human admin
    - api_key: newly created, scoped to specific permissions
    """

    def __init__(self, app, storage):
        self.storage = storage
        self._permission_map: dict[str, Permission] = {}

    async def __call__(self, scope, receive, send):
        ...

class TokenManager:
    """Create, validate, rotate, and revoke access tokens."""

    async def create_token(
        self, principal_id: str, role: Role,
        scopes: list[Permission] | None = None,
        expires_in: int | None = None,
    ) -> str:
        """Generate a signed JWT with role and optional scopes."""

    async def validate_token(self, token: str) -> TokenInfo:
        """Validate and decode a token. Returns principal info."""

    async def revoke_token(self, token: str) -> None:
        """Immediately revoke a token (add to blocklist)."""

    async def rotate_token(self, old_token: str) -> str:
        """Revoke old token, issue new one with same permissions."""
```

### B.5 API Endpoint Permission Mapping

```python
# router.py — endpoint decorator pattern:
@router.post("/api/v1/agents/register")
@requires(Permission.AGENT_REGISTER)  # or Role.AGENT, Role.ADMIN
async def agent_register(...): ...

@router.post("/api/v1/agents/{agent_id}/approve")
@requires(Permission.AGENT_APPROVE)  # ADMIN or SUPERADMIN only
async def agent_approve(...): ...

@router.get("/api/v1/discussions")
@requires(Permission.DISCUSSION_VIEW)  # Any authenticated principal
async def list_discussions(...): ...

@router.delete("/api/v1/tenants/{tenant_id}")
@requires(Permission.TENANT_DELETE)  # SUPERADMIN only
async def delete_tenant(...): ...
```

### B.6 Token Scoping and Rotation

```python
class TokenScope(BaseModel):
    """Optional narrowing of permissions for a specific token."""
    permissions: list[Permission]  # Subset of role permissions
    tenant_id: str | None = None   # Limit to specific tenant
    expires_at: datetime | None    # Auto-expire
    max_uses: int | None = None    # One-time token support
    source_ip: str | None = None   # IP restriction
```

Token rotation support:
- `POST /api/v1/auth/tokens` — create new token
- `POST /api/v1/auth/tokens/{id}/rotate` — rotate (revoke old, issue new)
- `DELETE /api/v1/auth/tokens/{id}` — revoke
- `GET /api/v1/auth/tokens` — list active tokens (admin only)

### B.7 WebSocket RBAC

WebSocket connections also need RBAC:
- On connect: validate token (as Phase 9.3 does today)
- Extract role and permissions from token
- Check permissions for each message type:
  - `SPEAK`: requires `discussion:view`
  - `VOTE`: requires `discussion:view`
  - `TASK_STATUS`: requires `task:execute`
  - `TASK_ACCEPT_RESULT`: requires `task:review`
- Observers can connect but only receive broadcasts, cannot send

### B.8 Audit Logging

New module: `agora/coordinator/audit.py`

```python
class AuditLogger:
    """Records security-relevant events for compliance and debugging."""

    async def log(
        self, action: str, principal_id: str,
        resource: str, result: str, details: dict | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Write an audit event to persistent storage."""

    async def query(
        self, principal_id: str | None = None,
        action: str | None = None, since: datetime | None = None,
    ) -> list[AuditEvent]:
        """Query audit trail with filters."""
```

Audit events stored per-tenant in `audit_log` table:

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT,
    result TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_audit_principal ON audit_log(tenant_id, principal_id);
CREATE INDEX idx_audit_time ON audit_log(tenant_id, created_at);
```

### B.9 Migration Path (Backward Compatibility)

Phase 10 RBAC must not break existing Phase 9 deployments:

1. **Default behavior**: If no RBAC config exists, all tokens grant `AGENT` role
   (preserves Phase 9 behavior where any valid token can do anything)
2. **Opt-in enforcement**: `AGORA_RBAC_ENFORCE=true` enables strict permission
   checks. Until then, RBAC is advisory (logged but not enforced)
3. **Admin token migration**: `AGORA_ADMIN_TOKEN` continues to work; it maps
   to `SUPERADMIN` role. New deployments should use `TokenManager` instead
4. **Database migration**: Add `roles`, `permissions`, `tokens`, `audit_log`
   tables in SCHEMA_VERSION 9

### B.10 Files to Create/Modify

| Area | Files | Action |
|---|---|---|
| RBAC middleware | NEW: `agora/coordinator/rbac.py` | Auth middleware, permission checker, decorators |
| Token manager | NEW: `agora/coordinator/token_manager.py` | JWT creation, validation, rotation, revocation |
| Audit logging | NEW: `agora/coordinator/audit.py` | Audit event logger + query |
| Data models | MODIFY: `agora/coordinator/models.py` | Add Role, Permission, TokenInfo, TokenScope |
| Router | MODIFY: `agora/coordinator/router.py` | Add @requires decorators to all endpoints |
| WS endpoint | MODIFY: `agora/coordinator/ws_endpoint.py` | RBAC check on WS connect + message |
| Storage schema | MODIFY: `agora/coordinator/storage/schema.py` | Add roles, tokens, audit_log tables |
| Storage layer | NEW: `agora/coordinator/storage/tokens.py` | Token CRUD |
| Config | MODIFY: `agora/coordinator/config.py` | Add RBAC config options |

## Part C: Plugin Ecosystem

### C.1 Goal

Allow third-party extensions to add functionality to Agora without modifying
core code. Plugins can intercept events, add API endpoints, register custom
voting methods, implement custom task verifiers, and more.

### C.2 Design: Plugin Architecture

```python
class PluginManifest(BaseModel):
    """Metadata about a plugin."""
    name: str                          # e.g., "agora-plugin-github-webhook"
    version: str                       # Semver
    description: str
    author: str
    capabilities: list[str]            # ["hook", "api", "voter", "verifier"]
    depends_on: list[str] = []         # Plugin dependencies
    min_agora_version: str = "0.10.0"


class AgoraPlugin(ABC):
    """Base class for all Agora plugins."""

    manifest: PluginManifest

    @abstractmethod
    async def on_load(self, coordinator: "PluginCoordinator") -> None:
        """Called when plugin is loaded. Register hooks, endpoints, etc."""

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when plugin is unloaded. Clean up resources."""

    async def health_check(self) -> bool:
        """Optional health check. Return False to trigger reload."""
        return True
```

### C.3 Hook System

```python
class HookPoint(str, Enum):
    """Lifecycle events that plugins can hook into."""

    # Discussion lifecycle
    DISCUSSION_CREATED = "discussion.created"
    DISCUSSION_STARTED = "discussion.started"
    DISCUSSION_CLOSED = "discussion.closed"

    # Round events
    ROUND_STARTED = "round.started"
    ROUND_COMPLETED = "round.completed"

    # Vote events
    VOTE_CAST = "vote.cast"
    VOTE_FINALIZED = "vote.finalized"

    # Task events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_VERIFIED = "task.verified"
    GRAPH_COMPLETED = "graph.completed"

    # Agent events
    AGENT_REGISTERED = "agent.registered"
    AGENT_APPROVED = "agent.approved"
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"


class HookContext(BaseModel):
    """Context passed to hook handlers."""
    hook: HookPoint
    motion_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None
    data: dict = Field(default_factory=dict)


class PluginCoordinator:
    """Manages plugin lifecycle and hooks."""

    def __init__(self):
        self._plugins: dict[str, AgoraPlugin] = {}
        self._hooks: dict[HookPoint, list[AgoraPlugin]] = {
            h: [] for h in HookPoint
        }

    def register_hook(self, plugin: AgoraPlugin, hook: HookPoint):
        """Register a plugin to receive a specific hook event."""

    async def fire_hook(self, hook: HookPoint, ctx: HookContext):
        """Fire all registered hooks for an event. Non-blocking (fire-and-forget)."""

    async def load_plugin(self, manifest: PluginManifest,
                          plugin_instance: AgoraPlugin) -> None:
        """Load and activate a plugin."""

    async def unload_plugin(self, name: str) -> None:
        """Unload and deactivate a plugin."""

    def get_plugin(self, name: str) -> AgoraPlugin | None:
        """Get a loaded plugin by name."""
```

### C.4 Plugin Extension Points

**1. Custom Voting Methods**

```python
class VotingMethodPlugin(AgoraPlugin):
    """Plugin that adds a custom voting method."""

    async def on_load(self, coordinator):
        coordinator.register_voting_method(
            name="quadratic_voting",
            handler=self.quadratic_vote_tally,
        )

    def quadratic_vote_tally(self, votes: list[Vote]) -> VoteResult:
        """Implement quadratic voting tally logic."""
```

**2. Custom Task Verifiers**

```python
class TaskVerifierPlugin(AgoraPlugin):
    """Plugin that adds a custom task verification strategy."""

    async def on_load(self, coordinator):
        coordinator.register_task_verifier(
            name="security_scan",
            handler=self.run_security_scan,
        )

    async def run_security_scan(self, task: TaskNode) -> VerifyResult:
        """Run bandit/semgrep on changed files."""
```

**3. Custom API Endpoints**

```python
class APIEndpointPlugin(AgoraPlugin):
    """Plugin that adds custom REST API endpoints."""

    async def on_load(self, coordinator):
        coordinator.register_api_route(
            method="GET",
            path="/api/v1/plugins/webhook",
            handler=self.handle_webhook,
        )

    async def handle_webhook(self, request: Request) -> JSONResponse:
        """Handle incoming webhook from external service."""
```

**4. Custom Discussion Policies**

```python
class DiscussionPolicyPlugin(AgoraPlugin):
    """Plugin that adds custom discussion rules."""

    async def on_load(self, coordinator):
        coordinator.register_discussion_policy(
            name="time_limit",
            check=self.enforce_time_limit,
        )

    async def enforce_time_limit(self, motion: Motion) -> PolicyResult:
        """Close discussion after N minutes regardless of consensus."""
```

### C.5 Plugin Sandboxing

Plugins run in the same process as the coordinator (no subprocess isolation
in Phase 10—that's Phase 12+). Safety measures:

```python
class PluginSandbox:
    """Resource limits and safety boundaries for plugins."""

    def __init__(self, plugin: AgoraPlugin):
        self.plugin = plugin
        self.max_memory_mb: int = 100
        self.max_cpu_seconds: int = 30
        self.allowed_imports: set[str] = {"agora", "json", "logging", "datetime"}
        self.blocked_imports: set[str] = {"os", "subprocess", "socket", "ctypes"}

    def check_import(self, module_name: str) -> bool:
        """Return False if the import is blocked."""

    async def enforce_timeout(
        self, coro, timeout: int = 30
    ) -> Any:
        """Run a coroutine with a timeout, raise on violation."""
        return await asyncio.wait_for(coro, timeout=timeout)
```

### C.6 Plugin Installation

Plugins are installed as PyPI packages (not Agora-specific format):

```bash
pip install agora-plugin-github-webhook
```

The plugin package must expose an entry point:

```toml
# pyproject.toml
[project.entry-points."agora.plugins"]
github_webhook = "agora_plugin_github_webhook:GitHubWebhookPlugin"
```

Agora discovers plugins via:

```python
# agora/coordinator/plugin_discovery.py
import importlib.metadata

def discover_plugins() -> list[AgoraPlugin]:
    """Scan installed packages for agora.plugins entry points."""
    plugins = []
    for ep in importlib.metadata.entry_points(group="agora.plugins"):
        plugin_cls = ep.load()
        plugins.append(plugin_cls())
    return plugins
```

### C.7 Plugin Lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│  Coordinator startup                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ 1. discover_plugins() → list of plugin classes           │ │
│  │ 2. For each plugin:                                      │ │
│  │    a. Validate manifest (version check, deps check)      │ │
│  │    b. Instantiate                                         │ │
│  │    c. Call on_load(coordinator)                           │ │
│  │    d. If on_load succeeds → plugin active                 │ │
│  │    e. If on_load fails → plugin disabled, log error       │ │
│  │ 3. Set up periodic health_check() for each plugin        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Runtime: hooks fire events to plugins                        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ fire_hook(DISCUSSION_CREATED, ctx)                       │ │
│  │   → GitHubWebhookPlugin.on_discussion_created(ctx)       │ │
│  │   → SlackNotifierPlugin.on_discussion_created(ctx)       │ │
│  │   → MetricsPlugin.on_discussion_created(ctx)             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Coordinator shutdown                                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ For each active plugin:                                  │ │
│  │   → on_unload()                                          │ │
│  │   → Remove from hook registrations                       │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### C.8 Plugin Marketplace (Future, not Phase 10)

Phase 10 implements the technical foundation. A plugin marketplace
(browse/install/rate plugins) is deferred to Phase 12+. Phase 10
only provides:
- Plugin discovery via entry points (local install)
- Plugin manifest validation
- Hook registration and firing

### C.9 Files to Create/Modify

| Area | Files | Action |
|---|---|---|
| Plugin base | NEW: `agora/coordinator/plugin.py` | AgoraPlugin, PluginManifest, HookPoint, HookContext |
| Plugin manager | NEW: `agora/coordinator/plugin_manager.py` | PluginCoordinator: load, unload, fire hooks |
| Plugin discovery | NEW: `agora/coordinator/plugin_discovery.py` | Entry point scanning |
| Plugin sandbox | NEW: `agora/coordinator/plugin_sandbox.py` | Import blocking, timeout enforcement |
| Extension points | NEW: `agora/coordinator/plugin_extensions.py` | VotingMethod, TaskVerifier, APIEndpoint registries |
| Coordinator main | MODIFY: `agora/coordinator/main.py` | Plugin discovery + loading on startup |
| Config | MODIFY: `agora/coordinator/config.py` | Plugin enable/disable config |
| Voting factory | MODIFY: `agora/coordinator/voting/factory.py` | Support plugin-registered voting methods |
| Task verify | MODIFY: `agora/coordinator/task_verify/` | Support plugin-registered verifiers |
| Router | MODIFY: `agora/coordinator/router.py` | Support plugin-registered API routes |

## Part D: Integration Testing (stretch goal)

### D.1 Goal

Phase 7 and Phase 9 have extensive unit tests (70+ test files, 62+ tests
all passing), but no end-to-end integration tests where multiple real
agents collaborate on a task. Phase 10's parallel execution makes this
more important.

### D.2 Test Architecture

```python
# tests/integration/test_parallel_execution.py
import pytest
import asyncio
from agora.coordinator.main import create_app
from agora.agent_client import AgoraClient, AgoraConfig

@pytest.mark.integration
async def test_two_agents_parallel_tasks():
    """Two agents execute independent tasks concurrently."""
    coordinator = await start_coordinator_process()
    agent_a = AgoraClient(...)
    agent_b = AgoraClient(...)
    await agent_a.connect()
    await agent_b.connect()
    # Create motion → task graph → execute in parallel
    # Assert both tasks completed within time window
    ...

@pytest.mark.integration
async def test_resource_conflict_serialization():
    """Two tasks touching same file are serialized."""
    ...
```

### D.3 Scope (defer to dedicated sub-task)

Integration testing is a stretch goal for Phase 10 and should be a dedicated
sub-task assigned after core development. The priority is Parts A, B, C.

## What NOT to do in Phase 10

- **No Web UI / Admin Dashboard** — Deferred to Phase 11+
- **No distributed (multi-coordinator) execution** — Phase 12+
- **No plugin marketplace UI** — Phase 12+
- **No OAuth / SSO integration** — Phase 12+
- **No fine-grained quota system** (per-tenant agent hours) — Phase 12+
- **No hot-reload plugins** — Phase 11+
- **No streaming task output** — Phase 11+

## Sub-Task Breakdown

### 10.1 Parallel Task Execution (dev-merger, ~5-6 tasks)

**10.1a Task models + storage updates** — ExecutionSlot, ResourceLock models,
new DB tables, SCHEMA_VERSION 9

**10.1b Parallel execution coordinator** — `task_parallel.py`: runqueue, slot
tracking, dynamic assignment, completion event handling

**10.1c Resource conflict detection** — `task_resource.py`: file-based lock
tracking, read/write sharing, conflict resolution policies

**10.1d New WebSocket messages** — TASK_STARTED, TASK_BLOCKED, TASK_UNBLOCKED,
TASK_RETRY, TASK_PROGRESS, GRAPH_COMPLETE in models.py + handlers

**10.1e Failure handling + retry** — Retry policy, partial success, abort-on-failure,
dependent task cascading

**10.1f Integration with Phase 9 task engine** — Wire parallel coordinator into
task_exec.py, update task_assign.py for dynamic re-assignment

### 10.2 RBAC (dev-merger, ~4-5 tasks)

**10.2a RBAC models + middleware** — `rbac.py`: Role, Permission, ROLE_PERMISSIONS,
@requires decorator, FastAPI middleware

**10.2b Token manager** — `token_manager.py`: JWT creation, validation, rotation,
revocation, blocklist

**10.2c Audit logging** — `audit.py`: audit_log table, structured event logger,
query API

**10.2d Endpoint permission wiring** — Add @requires to all router endpoints,
update WS endpoint for RBAC checks

**10.2e Storage + migration** — roles, tokens, audit_log tables, SCHEMA_VERSION 9,
backward compatibility with Phase 9 tokens

### 10.3 Plugin Ecosystem (dev-merger, ~4-5 tasks)

**10.3a Plugin base + manifest** — `plugin.py`: AgoraPlugin ABC, PluginManifest,
HookPoint, HookContext

**10.3b Plugin coordinator** — `plugin_manager.py`: PluginCoordinator, load/unload,
hook registration + firing (fire-and-forget)

**10.3c Plugin discovery** — `plugin_discovery.py`: entry point scanning,
manifest validation, dependency checking

**10.3d Plugin sandbox** — `plugin_sandbox.py`: import blocking, timeout
enforcement, memory limits (advisory)

**10.3e Extension points** — `plugin_extensions.py`: VotingMethod registry,
TaskVerifier registry, APIEndpoint registry, DiscussionPolicy registry

### 10.4 Integration + Documentation (dev-merger, ~2 tasks)

**10.4a Integration wiring** — All three parts connected, coordinator startup
loads plugins + RBAC middleware, parallel executor replaces sequential

**10.4b Documentation** — Update ARCHITECTURE.md (v0.9.3 → v0.10.0), API.md
(add RBAC endpoints, new WS messages), DESIGN-phase10.md summary

### 10.5 Integration Testing (dev-merger, ~1 task, stretch goal)

**10.5a Parallel execution integration tests** — Multi-agent test fixtures,
end-to-end task graph execution, resource conflict scenarios

## Files Summary

| Phase | New Files | Modified Files | DB Changes |
|---|---|---|---|
| 10.1 Parallel | task_parallel.py, task_resource.py | task_models.py, models.py, ws_handlers.py, task_exec.py, task_assign.py, storage/schema.py, storage/tasks.py | execution_slots, resource_locks tables |
| 10.2 RBAC | rbac.py, token_manager.py, audit.py, storage/tokens.py | models.py, router.py, ws_endpoint.py, storage/schema.py, config.py | roles, tokens, audit_log tables |
| 10.3 Plugins | plugin.py, plugin_manager.py, plugin_discovery.py, plugin_sandbox.py, plugin_extensions.py | main.py, config.py, voting/factory.py, task_verify/__init__.py, router.py | plugin_registry table |
| 10.4 Docs | — | ARCHITECTURE.md, API.md, DESIGN-phase10.md | — |
| 10.5 Tests | tests/integration/test_parallel_execution.py, tests/integration/conftest.py | — | — |

## Estimated Effort

| Part | Complexity | Dev Tasks | Review Tasks | Total Effort |
|---|---|---|---|---|
| 10.1 Parallel | High | ~6 | ~2 | 4-6 days |
| 10.2 RBAC | Medium | ~5 | ~2 | 3-4 days |
| 10.3 Plugins | High | ~5 | ~2 | 4-5 days |
| 10.4 Docs | Low | ~1 | ~1 | 1 day |
| 10.5 Tests | Medium | ~1 | ~1 | 1-2 days |
| **Total** | — | **~18** | **~8** | **13-18 days** |
