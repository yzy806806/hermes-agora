# DESIGN-phase9.md — Phase 9: Platform Independence + Task Execution + Agent Protocol

> Version: v0.9.0-draft | Date: 2026-06-09 | Author: planner

## Background

Phase 1-8 delivered Agora v0.8.0 with full discussion engine, voting, quality guard,
fault tolerance, bootstrap, observability, multi-tenancy, and a light dashboard.

Three major gaps remain before Agora can fulfill the ROADMAP vision as a standalone
multi-agent platform:

1. **Still a Hermes plugin** — Agora is `plugin.yaml` + `__init__.py`, not a
   standalone deployable service
2. **No task execution** — discussions produce decisions but those decisions
   don't automatically turn into work (no task graph, no assign, no execution)
3. **Agent protocol is ad-hoc** — registration is a simple HTTP POST with no
   heartbeat, no capability declaration, no authentication

These three are interlinked: platform independence unlocks Docker-deployable
agent containers; task execution needs a proper agent protocol to assign work;
agent protocol needs platform independence to work outside Hermes.

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Platform Independence | ★★★★★ | ★★★★★ | ★★★★ | Medium | **Phase 9 Core** |
| Task Execution Engine | ★★★★★ | ★★★★★ | ★★★ | High | **Phase 9 Core** |
| Agent Registration Protocol | ★★★★★ | ★★★★★ | ★★★★ | Medium | **Phase 9 Core** |
| API Rate Limiting (TPM) | ★★★★ | ★★★★ | ★★★★★ | Low | **Phase 9 Core** |
| Plugin Ecosystem | ★★★ | ★★ | ★★★ | High | Defer to Phase 10 |
| Performance Optimization | ★★★ | ★★ | ★★★★ | Medium | Defer to Phase 10 |

### Why these four together

1. Platform independence is the gatekeeper — without it, Task Execution and Agent
   Protocol can't reach non-Hermes agents
2. Task Execution and Agent Protocol are tightly coupled — tasks need agent
   capabilities to assign, protocol needs task definitions to be useful
3. API Rate Limiting is small enough to bundle and is needed before external
   agents can safely connect

## Architecture Target (end of Phase 9)

```
                        ┌─────────────────────────────────┐
                        │       Agora Platform             │
                        │  (standalone, pip install agora) │
                        │  ┌──────────┐ ┌───────────────┐  │
                        │  │ REST API │ │ WebSocket Hub  │  │
                        │  └────┬─────┘ └──────┬────────┘  │
                        │  ┌────┴──────────┐ ┌─┴──────────┐ │
                        │  │  Discussion   │ │   Task      │ │
                        │  │  Engine       │ │  Execution  │ │
                        │  │  (Phases 1-8) │ │  Engine     │ │
                        │  └───────────────┘ └─────────────┘ │
                        │  ┌───────────┐ ┌─────────────────┐ │
                        │  │ Agent     │ │ API Rate        │ │
                        │  │ Registry  │ │ Limiter (TPM)   │ │
                        │  └───────────┘ └─────────────────┘ │
                        │  ┌───────────────────────────┐     │
                        │  │ Storage (multi-tenant)    │     │
                        │  └───────────────────────────┘     │
                        └────────────┬───────────────────────┘
                                     │ HTTP/WS (standard)
            ┌────────────────────────┼────────────────────────┐
            ↓                        ↓                        ↓
       ┌─────────┐            ┌─────────┐            ┌─────────┐
       │ Hermes  │            │ Docker  │            │ Custom  │
       │ Agent   │            │ Agent   │            │ HTTP    │
       │ (agora- │            │ (agora- │            │ Agent   │
       │  client)│            │  client)│            │ (any    │
       └─────────┘            └─────────┘            │  lang)  │
                                                     └─────────┘
```

## Part A: Platform Independence

### A.1 Goal

Decouple Agora from Hermes plugin system so it can be:

- `pip install agora` — standalone Python package
- `docker run agora-coordinator` — Docker image
- Accessed by any HTTP/WebSocket client

### A.2 What Changes

**Package rename**: `hermes-agora` → `agora` (top-level package)

**Entry points**:
- `agora-coordinator` CLI: `agora coordinator serve --port 8765`
- `AgoraClient`: stays in `agora.agent_client` (import works without Hermes)

**Remove plugin machinery**:
- Delete `__init__.py` register() hook, `plugin.yaml`
- Delete `commands.py`, `cmd_*.py` (Hermes slash commands — coordinator
  doesn't need them; Hermes profile can use AgoraClient directly)

**New config system**:
- `coordinator/config.py` currently uses pydantic-settings with env vars
- Keep this, but add support for a `config.yaml` or `agora.toml`
- Default: `~/.agora/config.yaml` with sane defaults (port 8765, db at
  `~/.agora/data/`)

**CLI entry point** (`agora/__main__.py` or `agora/cli.py`):
```
usage: agora [-h] {serve,agent} ...

agora serve     Start the coordinator server
agora agent     Run an agent (connect to coordinator)
agora --version Show version
```

### A.3 New Project Structure

```
agora/
├── __init__.py              # package init, version
├── cli.py                   # CLI entry: serve / agent
├── coordinator/             # (same structure, renamed from
│   ├── main.py              #   coordinator/ to agora/coordinator/)
│   ├── config.py
│   ├── models.py
│   ├── ...                  # existing coordinator/* files
├── agent_client/            # existing client lib
├── tests/                   # existing tests (move)
├── docs/                    # existing docs
├── pyproject.toml           # new: build config
├── Dockerfile               # new: coordinator image
├── Dockerfile.agent         # new: agent image template
└── docker-compose.yaml      # new: dev setup
```

### A.4 Hermes Integration Path

Existing Hermes profiles use Agora via the client library:

```python
# In a Hermes profile's tool plugin:
from agora.agent_client import AgoraClient, AgoraConfig

client = AgoraClient(AgoraConfig(
    coordinator_url="http://localhost:8765",
    agent_id="planner",
))
```

No longer a "plugin" — just a Python library dependency.

### A.5 Deployment Models

| Mode | Command | When to use |
|---|---|---|
| Local dev | `agora serve` | Developing Agora itself |
| Docker | `docker run agora-coordinator` | Production, CI |
| docker-compose | `docker compose up` | Full stack (coordinator + agents) |
| pip install | `pip install agora` | Using as a library |

## Part B: Task Execution Engine

### B.1 Goal

Automatic flow from discussion to execution:

```
Discussion closes → Coordinator generates TaskGraph → Auto-assign agents → Execute tasks → Verify results → Accept/reject
```

### B.2 Data Model

```python
class TaskStatus(str, Enum):
    PENDING = "pending"       # Not yet assigned
    ASSIGNED = "assigned"     # Assigned to agent, not started
    RUNNING = "running"       # Agent is working
    DONE = "done"             # Completed, awaiting review
    ACCEPTED = "accepted"     # Reviewed and accepted
    REJECTED = "rejected"     # Reviewed and rejected, back to pending
    FAILED = "failed"         # Execution failed (error/timeout)

class TaskNode(BaseModel):
    """A single task node in the task graph."""
    id: str                   # UUID
    motion_id: str            # Source discussion
    title: str                # Human-readable
    description: str          # Detailed spec
    status: TaskStatus
    assigned_to: str | None   # agent_id
    required_capabilities: list[str]  # e.g. ["code", "test", "review"]
    depends_on: list[str]     # Task IDs that must finish first
    artifact_paths: list[str] # Files produced (for review)
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

class TaskGraph(BaseModel):
    """DAG of tasks from a discussion."""
    id: str
    motion_id: str
    tasks: list[TaskNode]
    created_at: datetime
```

### B.3 Core Modules

**Task Generator** (`coordinator/task_gen/`):
- Reads a closed discussion's `result.rationale` and `action_items`
- Uses an LLM call (coordinator's own model) to decompose into a task graph
- Output: `TaskGraph` with dependency edges
- Simple heuristic fallback: one task per action_item, sequential

**Task Assigner** (`coordinator/task_assign.py`):
- Reads agent capabilities from the registry
- Matches `required_capabilities` → available agents
- Round-robin for equal-capability agents
- Respects agent load (max concurrent tasks per agent)

**Task Execution Manager** (`coordinator/task_exec.py`):
- State machine: PENDING → ASSIGNED → RUNNING → DONE → ACCEPTED/REJECTED
- WebSocket messages for task lifecycle:
  - `TASK_ASSIGNED` → agent gets a new task
  - `TASK_STATUS_UPDATE` → agent reports progress
  - `TASK_COMPLETED` → agent finishes, files produced
  - `TASK_FAILED` → agent errors out

**Task Verifier** (`coordinator/task_verify.py`):
- When a task is DONE, coordinator triggers verification
- Simple checks: file exists, tests pass (if test files exist)
- Delegates full review to another agent (releaser/reviewer role)
- Auto-accepts simple tasks, routes complex ones to review

### B.4 New API Endpoints

```
# Task management
POST   /api/v1/task-graphs/{motion_id}        # Generate from discussion
GET    /api/v1/task-graphs/{graph_id}          # Get task graph
GET    /api/v1/tasks?agent_id=&status=         # List tasks
PATCH  /api/v1/tasks/{task_id}                 # Update task status
GET    /api/v1/tasks/{task_id}/artifacts       # List produced files

# Task execution (WebSocket messages)
TASK_ASSIGNED     → server pushes task to agent
TASK_STATUS       → agent → server (RUNNING/DONE/FAILED)
TASK_VERIFIED     → server → reviewing agent
TASK_ACCEPT_RESULT → reviewing agent → server
```

### B.5 Bounded Scope

Phase 9 task engine constraints:
- **No parallel task fan-out** — sequential execution within graph-level
  (parallel is Phase 10)
- **No task re-execution/retry** — tasks fail once and go to FAILED
- **No dynamic task insertion** — graph is static after generation
- **Only one graph per discussion**

## Part C: Agent Registration Protocol

### C.1 Goal

Standardize how agents connect to Agora, replacing the current ad-hoc
`/agents/register` POST + manual WS handshake.

### C.2 Registration Flow

```
1. Agent → POST /api/v1/agents/register
   {
     "agent_id": "dev-alpha",
     "name": "Developer Alpha",
     "capabilities": ["code", "test", "deploy"],
     "agent_type": "hermes",        # hermes|docker|cli|custom
     "model": "claude-sonnet-4",
     "max_concurrent_tasks": 2,
     "auth_token": "sk-xxx"         # API key for auth
   }

2. Coordinator → 201 Created
   {
     "agent_id": "dev-alpha",
     "status": "approved",          # or "pending" if approval required
     "agent_token": "ag-xxx"        # Token for WS auth
   }

3. Agent → WebSocket /ws?agent_id=dev-alpha&token=ag-xxx
   Authorization: Bearer ag-xxx via header or query param

4. Coordinator validates token → WELCOME message

5. Agent sends periodic HEARTBEAT (every 30s, configurable)
   {
     "type": "HEARTBEAT",
     "agent_id": "dev-alpha",
     "load": 0.5,                   # Current load ratio
     "active_tasks": ["t-123"]
   }
```

### C.3 Agent Capabilities

Standardized capability taxonomy:

```python
CAPABILITIES = {
    # Development
    "code":        "Write and modify code",
    "test":        "Write and run tests",
    "debug":       "Debug and fix issues",
    "refactor":    "Restructure existing code",

    # Review & Quality
    "review":      "Review code and PRs",
    "security":    "Security audit",
    "docs":        "Write documentation",

    # Design & Planning
    "design":      "Architecture and design",
    "planning":    "Task breakdown and planning",
    "research":    "Research and investigation",

    # Operations
    "deploy":      "Deploy to production",
    "release":     "Create releases",
    "monitor":     "Monitor and alert",
}
```

### C.4 Agent Configuration

Per-agent settings stored in coordinator:

```python
class AgentConfig(BaseModel):
    max_concurrent_tasks: int = 2
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 120     # Mark offline if no heartbeat
    tpm_limit: int = 10000                   # Tokens per minute
    allowed_discussion_roles: list[str] = ["participant"]
    auto_accept_tasks: bool = False          # Skip review for this agent's tasks
```

### C.5 Authentication & Authorization (Phase 9 Scope)

Phase 9 implements basic auth, not full security:

- **Agent-level API keys**: each agent gets a unique `agent_token` on
  registration (random UUID). All WS connections require it.
- **Approve-on-register (default)**: new agents auto-approve (for trusted
  local dev). Production can flip `AGORA_REQUIRE_APPROVAL=true`.
- **Coordinator admin token**: a single `AGORA_ADMIN_TOKEN` env var
  protects tenant/agent management endpoints. Without it, anyone on localhost
  can create tenants. Phase 10+ will add proper RBAC.

**What Phase 9 explicitly does NOT do:**
- No multi-user auth (login/password/OAuth)
- No role-based access control beyond agent capabilities
- No audit logging (beyond existing events)
- No token rotation or expiry

## Part D: API Rate Limiting (TPM)

### D.1 Goal

Each agent has a configurable tokens-per-minute limit on LLM API calls.
Coordinator tracks and enforces this.

### D.2 Design

```python
class TokenRateLimiter:
    """Per-agent token budget tracking."""

    def __init__(self):
        self._budgets: dict[str, TokenBucket] = {}

    def configure(self, agent_id: str, tpm: int) -> None:
        """Set TPM limit for an agent."""
        self._budgets[agent_id] = TokenBucket(capacity=tpm, refill_rate=tpm/60)

    def consume(self, agent_id: str, tokens: int) -> bool:
        """Try to consume tokens. Returns False if rate limited."""
        ...

    def remaining(self, agent_id: str) -> float:
        """Remaining tokens in current window."""
        ...
```

### D.3 Integration Points

Rate limiting applies to the **agent's LLM API calls**, not to Agora
coordinator calls. This is enforced by the agent itself using the
coordinator's rate limit configuration:

1. Agent registers with `tpm_limit` in config
2. Coordinator stores the limit
3. Agent fetches its config on connect (WELCOME payload includes
   `rate_limit.tpm`)
4. Agent enforces locally — Agora doesn't proxy LLM calls

Coordinator provides an endpoint for rate limit reporting:

```
POST /api/v1/agents/{agent_id}/rate-limit/report
{"tokens_used": 500, "model": "claude-sonnet-4"}

GET /api/v1/agents/{agent_id}/rate-limit
→ {"tpm_limit": 10000, "tokens_used_this_minute": 3500, "remaining": 6500}
```

### D.4 Agency Client Integration

The `AgoraClient` library adds a `RateLimitTracker`:

```python
client = AgoraClient(config)

# Before LLM call:
if not client.rate_limiter.check(estimated_tokens):
    await asyncio.sleep(remaining_wait)

# After LLM call:
client.rate_limiter.report(actual_tokens_used)
```

## What NOT to do in Phase 9

- **Not building a full Web UI** — Dashboard exists for monitoring.
  Full admin UI is Phase 11+
- **Not parallel task execution** — Sequential only. Fan-out is Phase 10.
- **Not Docker agent registry / marketplace**
- **Not GitHub OAuth integration**
- **Not e2e test framework** — Integration tests exist from Phase 7.
  True e2e with real agents is Phase 10+
- **Not plugin ecosystem** — Deferred from Phase 8, still deferred.
- **Not horizontal scaling** — Single coordinator is sufficient.
- **Not RBAC** — API keys only, no user roles.

## Detailed Design Files

See companion files for task-level implementation details:

- `docs/DESIGN-phase9-task-engine.md` — Task graph schema, state machine, API specs
- `docs/DESIGN-phase9-agent-protocol.md` — Registration flow, heartbeat format, auth tokens
- `docs/DESIGN-phase9-rate-limit.md` — Token bucket algorithm, client integration

## Files That Change

| Area | Files |
|---|---|
| Package rename | `__init__.py`, `plugin.yaml` (delete), `commands.py` + `cmd_*.py` (delete) |
| CLI | NEW: `cli.py`, `__main__.py` |
| Build | NEW: `pyproject.toml`, `Dockerfile`, `Dockerfile.agent`, `docker-compose.yaml` |
| Config | `coordinator/config.py` (add yaml/toml + env override) |
| Task Engine | NEW: `coordinator/task_gen/`, `coordinator/task_assign.py`, `coordinator/task_exec.py`, `coordinator/task_verify.py` |
| Agent Protocol | `coordinator/models.py` (add agent_type, agent_token, AgentConfig), `coordinator/ws_endpoint.py` (add auth check, heartbeat), `coordinator/ws_handlers.py` (add HEARTBEAT handler) |
| Rate Limit | `coordinator/rate_limiter.py` (extend for TPM), `agent_client/client.py` (add RateLimitTracker) |
| Docs | `ARCHITECTURE.md`, `API.md`, `README.md` |

## Files NOT Changed

- `coordinator/voting/*`, `coordinator/bootstrap/*` — no changes
- `coordinator/observability/*` — no changes
- `coordinator/tenant/*` — no changes
- `coordinator/quality_*.py`, `coordinator/*.py` (discussion engine) — no changes
- `agent_client/ws_pool.py` — no changes (already supports reconnection)

## Sub-Task Breakdown

### 9.1 Platform Independence (dev-merger, ~3-4 tasks)

**9.1a Package restructure** — Move to `agora/`, add `pyproject.toml`, CLI
**9.1b Docker image** — `Dockerfile` for coordinator, `docker-compose.yaml`
**9.1c Config overhaul** — config.yaml support, env override, ~/.agora/ dir

### 9.2 Task Execution Engine (dev-merger, ~4-5 tasks)

**9.2a Task models + storage** — TaskNode, TaskGraph, DB schema, Storage methods
**9.2b Task generator** — Discussion → TaskGraph (LLM + heuristic fallback)
**9.2c Task assigner** — Capability matching, round-robin, load tracking
**9.2d Task execution + WebSocket** — State machine, TASK_* messages, lifecycle
**9.2e Task verification** — Artifact check, delegate to reviewer agent

### 9.3 Agent Registration Protocol (dev-merger, ~3 tasks)

**9.3a Agent model updates** — agent_type, agent_token, AgentConfig model
**9.3b Registration + auth flow** — POST /register → token → WS auth
**9.3c Heartbeat + capability declaration** — HEARTBEAT handler, capability schema

### 9.4 API Rate Limiting (dev-merger, ~2 tasks)

**9.4a Token rate limiter** — TokenBucket + TPM config + report endpoint
**9.4b Client integration** — AgoraClient.RateLimitTracker

### 9.5 Integration + Docs (dev-merger, ~1 task)

**9.5a Integration + docs** — All parts wired together, ARCHITECTURE.md updated,
tests adapted to new package structure

### Total: ~13-15 sub-tasks for dev-merger

## Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Package rename breaks existing tests | Medium | Rename in dedicated first task, verify all tests pass before continuing |
| Task graph generation is unreliable | High | Start with heuristic (no LLM), add LLM as enhancement. Heuristic: one task per action_item |
| Agent auth is too simple for production | Low | Accept for Phase 9. Document that `AGORA_REQUIRE_APPROVAL=true` is the production path |
| Too many sub-tasks blocks dev-merger | Medium | Use parent-child chains so dev-merger can work sequentially, maintainer can prioritize |