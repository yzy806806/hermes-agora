# DESIGN-phase9-task-engine.md — Phase 9.2: Task Execution Engine Detailed Design

> Version: v0.9.0-draft | Date: 2026-06-09 | Author: planner
> Parent: docs/DESIGN-phase9.md Part B

## Background

Phase 9 Part B defines the Task Execution Engine at a high level. This document
provides the detailed implementation design for each sub-task: data models,
storage schema, API endpoints, WebSocket messages, and file-level
implementation plan.

The engine transforms closed discussions into executable task graphs, assigns
tasks to capable agents, tracks execution via WebSocket, and verifies results.

## Architecture Overview

```
Discussion closes (Motion.status=CLOSED, action_items populated)
        │
        ▼
┌───────────────────┐
│  Task Generator    │  Reads motion.action_items + rationale
│  (task_gen/)       │  → LLM call to decompose into TaskGraph
│                    │  → Heuristic fallback: 1 task per action_item
└───────┬───────────┘
        │ TaskGraph (DAG of TaskNodes)
        ▼
┌───────────────────┐
│  Task Assigner     │  Reads agent capabilities from registry
│  (task_assign.py)  │  → Match required_capabilities → agents
│                    │  → Round-robin for equal-capability agents
│                    │  → Respects max_concurrent_tasks
└───────┬───────────┘
        │ Assignments via WebSocket TASK_ASSIGNED
        ▼
┌───────────────────┐
│  Task Executor     │  State machine: PENDING→ASSIGNED→RUNNING→DONE
│  (task_exec.py)    │  WebSocket messages: TASK_ASSIGNED, TASK_STATUS,
│                    │  TASK_COMPLETED, TASK_FAILED
└───────┬───────────┘
        │ Task DONE
        ▼
┌───────────────────┐
│  Task Verifier     │  Check artifacts exist, tests pass
│  (task_verify.py)  │  Auto-accept simple tasks
│                    │  Delegate complex review to reviewer agent
└───────────────────┘
```

---

## 9.2a: Task Models + Storage

### Files to Create

```
agora/coordinator/task_models.py       # TaskNode, TaskGraph, TaskStatus, enums
agora/coordinator/storage/tasks.py     # Task CRUD operations
```

### Files to Modify

```
agora/coordinator/storage/schema.py    # Add task tables (bump SCHEMA_VERSION to 6)
agora/coordinator/storage/storage.py   # Add task CRUD delegation methods
```

### Data Models (`task_models.py`)

```python
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"         # Not yet assigned
    ASSIGNED = "assigned"       # Assigned to agent, not started
    RUNNING = "running"         # Agent is working
    DONE = "done"               # Completed, awaiting verification
    ACCEPTED = "accepted"       # Verified and accepted
    REJECTED = "rejected"       # Verified and rejected, back to PENDING
    FAILED = "failed"           # Execution failed (error/timeout)


class TaskNode(BaseModel):
    """A single task node in the task graph."""
    id: str                                          # UUID
    graph_id: str                                    # Parent TaskGraph ID
    motion_id: str                                   # Source discussion
    title: str                                       # Human-readable
    description: str                                 # Detailed spec
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None                # agent_id
    required_capabilities: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)  # Task IDs
    artifact_paths: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None              # Set on FAILED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskGraph(BaseModel):
    """DAG of tasks generated from a discussion."""
    id: str                                          # UUID
    motion_id: str                                   # Source discussion
    tasks: list[TaskNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### DB Schema Changes (`schema.py`)

Bump `SCHEMA_VERSION` from 5 to 6. Add two new tables:

```sql
CREATE TABLE IF NOT EXISTS task_graphs (
    id TEXT PRIMARY KEY,
    motion_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    motion_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_to TEXT,
    required_capabilities TEXT,        -- JSON array
    depends_on TEXT,                   -- JSON array of task IDs
    artifact_paths TEXT,               -- JSON array
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (graph_id) REFERENCES task_graphs(id) ON DELETE CASCADE,
    FOREIGN KEY (motion_id) REFERENCES motions(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_graph ON tasks(graph_id);
CREATE INDEX IF NOT EXISTS idx_tasks_motion ON tasks(motion_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to);
```

### Storage Methods (`storage/tasks.py` + `storage/storage.py`)

New module `storage/tasks.py` with async functions:

```python
# storage/tasks.py — each function takes an aiosqlite.Connection as first arg

async def create_task_graph(db, graph_id: str, motion_id: str) -> dict:
    """Insert a new TaskGraph row."""

async def get_task_graph(db, graph_id: str) -> Optional[dict]:
    """Get TaskGraph by ID, including all tasks."""

async def get_task_graph_by_motion(db, motion_id: str) -> Optional[dict]:
    """Get TaskGraph by motion_id."""

async def create_task(db, task: TaskNode) -> dict:
    """Insert a single TaskNode row."""

async def get_task(db, task_id: str) -> Optional[dict]:
    """Get a single task by ID."""

async def list_tasks(db, graph_id: str = None, agent_id: str = None,
                     status: str = None, limit: int = 100,
                     offset: int = 0) -> list[dict]:
    """List tasks with optional filters."""

async def update_task_status(db, task_id: str, status: str,
                             assigned_to: str = None,
                             error_message: str = None,
                             artifact_paths: list[str] = None) -> None:
    """Update task status and related fields."""

async def get_agent_task_count(db, agent_id: str,
                                active_only: bool = True) -> int:
    """Count active tasks for an agent (ASSIGNED + RUNNING)."""
```

Storage class gets delegation methods:

```python
# In storage/storage.py — add:
from . import tasks as _tasks

async def create_task_graph(self, graph_id: str, motion_id: str) -> dict:
    async with self._connection() as db:
        return await _tasks.create_task_graph(db, graph_id, motion_id)

async def get_task_graph(self, graph_id: str) -> Optional[dict]:
    ...

async def get_task_graph_by_motion(self, motion_id: str) -> Optional[dict]:
    ...

async def create_task(self, task: TaskNode) -> dict:
    ...

async def get_task(self, task_id: str) -> Optional[dict]:
    ...

async def list_tasks(self, **kwargs) -> list[dict]:
    ...

async def update_task_status(self, task_id: str, **kwargs) -> None:
    ...

async def get_agent_task_count(self, agent_id: str, active_only: bool = True) -> int:
    ...
```

### Key Design Decisions

1. **capabilities/depends_on/artifact_paths stored as JSON text** — consistent
   with existing pattern (agents.capabilities, motions.action_items).
2. **One TaskGraph per motion (UNIQUE constraint)** — Phase 9 constraint: no
   re-generation.
3. **TaskNode is a Pydantic model for in-memory use; storage layer uses dicts**
   — consistent with existing Storage pattern (all CRUD returns dict, not
   Pydantic models).
4. **SCHEMA_VERSION bump to 6** — existing migration pattern in schema.py.

---

## 9.2b: Task Generator

### Files to Create

```
agora/coordinator/task_gen/__init__.py    # Public API
agora/coordinator/task_gen/generator.py   # Core generation logic
agora/coordinator/task_gen/prompts.py     # LLM prompt templates
agora/coordinator/task_gen/heuristic.py   # Heuristic fallback
```

### Key Classes/Functions

```python
# task_gen/__init__.py

async def generate_task_graph(
    motion: dict,            # Motion row from storage
    storage: Storage,        # For reading discussion context
    llm_call,                # Async callable: (prompt) -> str
) -> TaskGraph:
    """Main entry point. Tries LLM first, falls back to heuristic."""
```

```python
# task_gen/generator.py

async def _llm_generate(motion: dict, storage: Storage, llm_call) -> TaskGraph:
    """Use LLM to decompose discussion into task graph.

    1. Read all messages from the discussion (storage.get_messages)
    2. Build a prompt with: motion title, description, rationale,
       action_items, and the full discussion transcript
    3. Call LLM with structured output instructions
    4. Parse JSON response into TaskNode list
    5. Validate: all depends_on refer to existing task IDs in the graph
    6. Return TaskGraph
    """

def _validate_graph(tasks: list[TaskNode]) -> None:
    """Validate DAG integrity:
    - No cycles
    - All depends_on IDs exist in the task list
    - No self-dependency
    Raises ValueError on invalid graph.
    """
```

```python
# task_gen/prompts.py

TASK_DECOMPOSITION_PROMPT = """\
You are a task decomposition engine. Given a closed discussion, generate
a task graph (DAG) for implementation.

Discussion Title: {title}
Description: {description}
Decision: {decision}
Rationale: {rationale}
Action Items: {action_items}

Discussion Transcript:
{transcript}

Output a JSON array of tasks. Each task has:
- "title": short human-readable name
- "description": detailed implementation spec
- "required_capabilities": array of capability strings from:
  [code, test, debug, refactor, review, security, docs, design, planning,
   research, deploy, release, monitor]
- "depends_on": array of task indices (0-based) that must complete first

Rules:
- Tasks should be granular (1 file or 1 concern per task)
- Dependencies should form a valid DAG (no cycles)
- Every task must have at least one capability
- Output ONLY the JSON array, no other text.

JSON:
"""
```

```python
# task_gen/heuristic.py

def heuristic_generate(motion: dict) -> TaskGraph:
    """Simple fallback: one task per action_item, sequential dependencies.

    Used when:
    - LLM call fails
    - LLM returns unparseable output
    - AGORA_TASK_GEN_MODE=heuristic (env override for testing)

    Each task gets required_capabilities=["code"] by default.
    Tasks are chained: task_N depends_on task_N-1.
    """
```

### Integration Point

The generator is triggered when a motion transitions to CLOSED with
`action_items` populated. This happens in the existing discussion close flow
(`ws_vote.py` or `state.py`). The coordinator calls `generate_task_graph()`
after closing the motion.

```python
# In the motion-close handler (e.g., state.py or ws_vote.py):
if motion["status"] == "closed" and motion.get("action_items"):
    from .task_gen import generate_task_graph
    task_graph = await generate_task_graph(motion, storage, llm_call)
    await storage.create_task_graph(task_graph.id, task_graph.motion_id)
    for task in task_graph.tasks:
        await storage.create_task(task)
    # Then trigger assignment
    from .task_assign import assign_tasks
    await assign_tasks(task_graph, storage, connection_hub)
```

### Key Design Decisions

1. **LLM callable is injected** — coordinator provides its own LLM; task_gen
   doesn't import a specific model client.
2. **Heuristic fallback is always available** — ensures the system degrades
   gracefully if LLM is unavailable.
3. **Prompt is in English** — consistent with existing codebase language.
4. **Validation before storage** — DAG integrity checked before persisting.

---

## 9.2c: Task Assigner

### Files to Create

```
agora/coordinator/task_assign.py    # Assignment logic
```

### Key Classes/Functions

```python
# task_assign.py

async def assign_tasks(
    graph: TaskGraph,
    storage: Storage,
    hub,                          # ConnectionHub for the tenant
) -> dict[str, str]:
    """Assign all PENDING tasks in a graph to capable agents.

    Returns: {task_id: agent_id} mapping.

    Algorithm:
    1. Get all PENDING tasks from the graph
    2. Sort by dependency order (tasks with no pending deps first)
    3. For each task:
       a. Find agents whose capabilities intersect required_capabilities
       b. Filter to online agents
       c. Filter to agents under max_concurrent_tasks
       d. Pick via round-robin among remaining candidates
       e. Update task: ASSIGNED, assigned_to=agent_id
       f. Send TASK_ASSIGNED via WebSocket
    4. Return assignments
    """

async def _find_capable_agents(
    required_caps: list[str],
    storage: Storage,
) -> list[dict]:
    """Find online agents matching required capabilities.

    Returns list of agent dicts sorted by capability match score (desc).
    """

def _round_robin_pick(
    candidates: list[dict],
    agent_loads: dict[str, int],
    max_concurrent: dict[str, int],
) -> str:
    """Pick the next agent using round-robin, respecting load limits.

    Skips agents at max capacity. Returns agent_id.
    """

async def _send_task_assignment(
    task: TaskNode,
    agent_id: str,
    hub,
) -> bool:
    """Send TASK_ASSIGNED WebSocket message to the agent.

    Returns True if sent successfully.
    """
```

### Assignment Algorithm Detail

```
Input: TaskGraph with PENDING tasks
Output: assignments dict

1. Build dependency resolution order:
   - ready_tasks = [t for t in tasks if all deps are DONE/ACCEPTED]
   - Process in BFS order through the DAG

2. For each ready task:
   a. candidates = agents where:
      - agent.capabilities ∩ task.required_capabilities ≠ ∅
      - agent.is_online == True
      - agent.active_task_count < agent.max_concurrent_tasks
   b. Sort candidates by capability_match_score (desc)
   c. Pick first candidate (round-robin index for ties)
   d. If no candidates: task stays PENDING, log warning
   e. If candidate found:
      - Update task: status=ASSIGNED, assigned_to=agent_id
      - Send TASK_ASSIGNED WS message
      - Increment agent's active_task_count

3. Return {task_id: agent_id}
```

### Capability Match Scoring

```python
def capability_match_score(agent_caps: list[str], required_caps: list[str]) -> float:
    """Score how well an agent's capabilities match requirements.

    Returns 0.0 to 1.0.
    - Exact match of all required: 1.0
    - Partial match: len(intersection) / len(required)
    - Extra capabilities don't hurt (agent can do more than needed)
    """
    if not required_caps:
        return 0.5  # Neutral for tasks with no specific requirements
    intersection = set(agent_caps) & set(required_caps)
    return len(intersection) / len(required_caps)
```

### Key Design Decisions

1. **Round-robin for equal-capability agents** — simple, fair, no complex
   scheduling needed for Phase 9.
2. **Load tracking via `get_agent_task_count()`** — queries DB for active
   tasks; no in-memory counter to lose on restart.
3. **Assignment is push-based** — coordinator pushes tasks to agents via
   WebSocket. Agents don't poll.
4. **No preemption** — once assigned, task stays with that agent until
   DONE/FAILED.

---

## 9.2d: Task Execution + WebSocket

### Files to Create

```
agora/coordinator/task_exec.py     # State machine + WS message handlers
```

### Files to Modify

```
agora/coordinator/models.py        # Add TASK_* MessageType values
agora/coordinator/ws_handlers.py   # Add task message dispatch
agora/coordinator/ws_endpoint.py   # Route TASK_* messages to handler
```

### State Machine

```
                    ┌─────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │ assign_tasks()
                         ▼
                    ┌─────────┐
                    │ASSIGNED │
                    └────┬─────┘
                         │ agent sends TASK_STATUS (status="running")
                         ▼
                    ┌─────────┐
                    │ RUNNING  │
                    └────┬─────┘
                    ┌────┴─────┐
                    │           │
                    ▼           ▼
               ┌────────┐  ┌────────┐
               │  DONE   │  │ FAILED │
               └───┬────┘  └────────┘
                   │
              ┌────┴─────┐
              │           │
              ▼           ▼
         ┌────────┐  ┌──────────┐
         │ACCEPTED│  │ REJECTED  │──→ PENDING (re-assign)
         └────────┘  └──────────┘
```

Valid transitions:
- PENDING → ASSIGNED (coordinator assigns)
- ASSIGNED → RUNNING (agent starts work)
- ASSIGNED → FAILED (agent rejects or times out)
- RUNNING → DONE (agent completes)
- RUNNING → FAILED (agent errors)
- DONE → ACCEPTED (verification passes)
- DONE → REJECTED (verification fails)
- REJECTED → PENDING (re-queue for assignment)

### WebSocket Message Types

Add to `models.py` MessageType enum:

```python
# Phase 9: Task execution
TASK_ASSIGNED = "TASK_ASSIGNED"
TASK_STATUS = "TASK_STATUS"
TASK_COMPLETED = "TASK_COMPLETED"
TASK_FAILED = "TASK_FAILED"
TASK_VERIFY = "TASK_VERIFY"
TASK_ACCEPT_RESULT = "TASK_ACCEPT_RESULT"
```

### Message Formats

```python
# Coordinator → Agent: new task assigned
{
    "type": "TASK_ASSIGNED",
    "motion_id": "m-xxx",
    "payload": {
        "task_id": "t-xxx",
        "title": "Implement rate limiter",
        "description": "Add token bucket rate limiter to API...",
        "required_capabilities": ["code", "test"],
        "depends_on": ["t-yyy"],
        "artifact_paths": []       # Expected output files (optional hint)
    }
}

# Agent → Coordinator: status update
{
    "type": "TASK_STATUS",
    "motion_id": "m-xxx",
    "payload": {
        "task_id": "t-xxx",
        "status": "running",       # "running" | "done" | "failed"
        "progress": "Writing tests...",  # Optional human-readable
        "error": None              # Set when status="failed"
    }
}

# Coordinator → Reviewer Agent: verify this task
{
    "type": "TASK_VERIFY",
    "motion_id": "m-xxx",
    "payload": {
        "task_id": "t-xxx",
        "title": "Implement rate limiter",
        "assigned_to": "dev-alpha",
        "artifact_paths": ["agora/coordinator/rate_limiter.py"],
        "description": "Add token bucket rate limiter..."
    }
}

# Reviewer Agent → Coordinator: verification result
{
    "type": "TASK_ACCEPT_RESULT",
    "motion_id": "m-xxx",
    "payload": {
        "task_id": "t-xxx",
        "accepted": true,          # true = ACCEPTED, false = REJECTED
        "feedback": "LGTM, tests pass, code clean"
    }
}
```

### Handler Implementation (`task_exec.py`)

```python
# task_exec.py

async def handle_task_status(
    agent_id: str,
    payload: dict,
    storage: Storage,
    hub,
) -> None:
    """Process TASK_STATUS from agent.

    Validates the transition, updates DB, and triggers next steps:
    - RUNNING → DONE: trigger verification
    - RUNNING → FAILED: log error, notify coordinator
    """
    task_id = payload.get("task_id")
    new_status = payload.get("status")

    task = await storage.get_task(task_id)
    if not task:
        await _send_error(hub, agent_id, "task_not_found", f"Task {task_id} not found")
        return

    if not _is_valid_transition(task["status"], new_status):
        await _send_error(hub, agent_id, "invalid_transition",
                          f"Cannot go from {task['status']} to {new_status}")
        return

    # Update DB
    await storage.update_task_status(
        task_id, new_status,
        error_message=payload.get("error"),
        artifact_paths=payload.get("artifact_paths", []),
    )

    # If DONE, trigger verification
    if new_status == "done":
        from .task_verify import verify_task
        await verify_task(task_id, storage, hub)

    # If FAILED, log event
    if new_status == "failed":
        await storage.log_event(
            "task.failed", f"Task {task_id} failed: {payload.get('error', '')}",
            motion_id=task["motion_id"], agent_id=agent_id,
        )


def _is_valid_transition(current: str, next_status: str) -> bool:
    """Check if state transition is allowed."""
    VALID = {
        "pending":   {"assigned"},
        "assigned":  {"running", "failed"},
        "running":   {"done", "failed"},
        "done":      {"accepted", "rejected"},
        "rejected":  {"pending"},
        "failed":    set(),         # Terminal state
        "accepted":  set(),         # Terminal state
    }
    return next_status in VALID.get(current, set())
```

### Integration into ws_handlers.py

Add dispatch in the main message handler (where REGISTER/SPEAK/VOTE are
dispatched):

```python
# In ws_handlers.py or ws_endpoint.py message loop:
if msg_type == MessageType.TASK_STATUS:
    await handle_task_status(agent_id, payload, storage, hub)
elif msg_type == MessageType.TASK_ACCEPT_RESULT:
    await handle_task_accept_result(agent_id, payload, storage, hub)
```

### Key Design Decisions

1. **Agent drives status updates** — coordinator doesn't poll; agents push
   TASK_STATUS messages.
2. **State machine is strict** — invalid transitions rejected with ERROR.
3. **FAILED is terminal in Phase 9** — no automatic retry (per DESIGN-phase9.md
   B.5 constraints).
4. **Verification is triggered automatically on DONE** — coordinator calls
   `verify_task()` without waiting for an external trigger.

---

## 9.2e: Task Verification

### Files to Create

```
agora/coordinator/task_verify.py    # Verification logic
```

### Key Classes/Functions

```python
# task_verify.py

async def verify_task(
    task_id: str,
    storage: Storage,
    hub,
) -> None:
    """Verify a completed task.

    Decision tree:
    1. Fetch task from storage
    2. Run auto-checks (artifact existence, test results if applicable)
    3. If auto-checks pass AND task is "simple":
       → Auto-accept (status=ACCEPTED)
    4. If auto-checks fail OR task is "complex":
       → Delegate to reviewer agent via TASK_VERIFY WS message
    """

async def _auto_verify(task: dict) -> tuple[bool, str]:
    """Run automated verification checks.

    Returns: (passed: bool, reason: str)

    Checks:
    1. Artifact files exist on disk (if artifact_paths specified)
    2. If test files exist in artifact_paths, run them and check pass/fail
    3. Basic file validity (non-empty, parseable)

    Phase 9 scope: only check #1 (file existence).
    #2 and #3 deferred to Phase 10.
    """

def _is_simple_task(task: dict) -> bool:
    """Determine if a task is simple enough for auto-accept.

    Simple tasks:
    - Single file change
    - No dependencies (or all deps already accepted)
    - Capabilities are only ["docs"] or ["code"] (not ["security", "deploy"])

    Returns True if auto-acceptable.
    """

async def _delegate_review(
    task: dict,
    storage: Storage,
    hub,
) -> None:
    """Send TASK_VERIFY to a reviewer agent.

    1. Find online agents with "review" capability
    2. Pick one (round-robin)
    3. Send TASK_VERIFY WS message
    4. If no reviewer available: leave task DONE, log warning
    """

async def handle_task_accept_result(
    agent_id: str,
    payload: dict,
    storage: Storage,
    hub,
) -> None:
    """Process TASK_ACCEPT_RESULT from reviewer agent.

    Updates task status to ACCEPTED or REJECTED.
    If REJECTED: set status back to PENDING for re-assignment.
    """
```

### Auto-Verify Logic Detail

```python
async def _auto_verify(task: dict) -> tuple[bool, str]:
    """Phase 9 auto-verification checks."""
    import os

    artifact_paths = task.get("artifact_paths") or []

    # Check 1: All declared artifacts exist
    missing = [p for p in artifact_paths if not os.path.exists(p)]
    if missing:
        return False, f"Missing artifacts: {', '.join(missing)}"

    # Check 2: If no artifacts declared, check if task description
    # mentions specific files (heuristic)
    if not artifact_paths:
        return True, "No artifacts declared; auto-accepting"

    return True, "All artifacts present"
```

### Key Design Decisions

1. **Auto-accept for simple tasks** — reduces review bottleneck. "Simple" is
   conservatively defined.
2. **Review delegation uses existing agent registry** — no special reviewer
   registration needed; any agent with "review" capability can review.
3. **No test execution in Phase 9** — just file existence check. Test running
   is Phase 10.
4. **Rejected tasks go back to PENDING** — can be re-assigned to same or
   different agent.

---

## API Endpoints

All endpoints are prefixed with `/api/v1/tenants/{tenant_id}` (multi-tenant
from Phase 8).

```
# Task Graph
POST   /api/v1/tenants/{tid}/task-graphs/{motion_id}
       → Generate task graph from a closed discussion
       ← 201 {graph_id, tasks: [...]}
       ← 409 if graph already exists for this motion
       ← 400 if motion not closed or has no action_items

GET    /api/v1/tenants/{tid}/task-graphs/{graph_id}
       → Get task graph with all tasks
       ← 200 {id, motion_id, tasks: [...], created_at}

# Tasks
GET    /api/v1/tenants/{tid}/tasks
       → List tasks (query: ?agent_id=&status=&graph_id=&limit=&offset=)
       ← 200 {tasks: [...], total, limit, offset}

GET    /api/v1/tenants/{tid}/tasks/{task_id}
       → Get single task detail
       ← 200 TaskNode

PATCH  /api/v1/tenants/{tid}/tasks/{task_id}
       → Update task (admin override for status, assigned_to)
       ← 200 updated TaskNode

GET    /api/v1/tenants/{tid}/tasks/{task_id}/artifacts
       → List artifact file paths for a task
       ← 200 {task_id, artifact_paths: [...]}
```

### Router Implementation

New file or addition to existing `router.py`:

```python
# In router.py or new task_router.py:

@router.post("/tenants/{tenant_id}/task-graphs/{motion_id}")
async def generate_task_graph(tenant_id: str, motion_id: str):
    ...

@router.get("/tenants/{tenant_id}/task-graphs/{graph_id}")
async def get_task_graph(tenant_id: str, graph_id: str):
    ...

@router.get("/tenants/{tenant_id}/tasks")
async def list_tasks(tenant_id: str, agent_id: str = None, ...):
    ...

@router.get("/tenants/{tenant_id}/tasks/{task_id}")
async def get_task(tenant_id: str, task_id: str):
    ...

@router.patch("/tenants/{tenant_id}/tasks/{task_id}")
async def update_task(tenant_id: str, task_id: str, body: TaskUpdateRequest):
    ...

@router.get("/tenants/{tenant_id}/tasks/{task_id}/artifacts")
async def get_task_artifacts(tenant_id: str, task_id: str):
    ...
```

---

## Summary of All Changes

### New Files (8)

| File | Purpose |
|------|---------|
| `agora/coordinator/task_models.py` | TaskNode, TaskGraph, TaskStatus |
| `agora/coordinator/storage/tasks.py` | Task CRUD DB operations |
| `agora/coordinator/task_gen/__init__.py` | Public API for task generation |
| `agora/coordinator/task_gen/generator.py` | LLM-based decomposition |
| `agora/coordinator/task_gen/prompts.py` | LLM prompt templates |
| `agora/coordinator/task_gen/heuristic.py` | Heuristic fallback |
| `agora/coordinator/task_assign.py` | Capability matching + assignment |
| `agora/coordinator/task_exec.py` | State machine + WS handlers |
| `agora/coordinator/task_verify.py` | Auto-verify + review delegation |

### Modified Files (5)

| File | Change |
|------|--------|
| `agora/coordinator/models.py` | Add TASK_* to MessageType enum |
| `agora/coordinator/storage/schema.py` | Add task_graphs + tasks tables, bump SCHEMA_VERSION to 6 |
| `agora/coordinator/storage/storage.py` | Add task CRUD delegation methods |
| `agora/coordinator/ws_handlers.py` | Add TASK_STATUS, TASK_ACCEPT_RESULT dispatch |
| `agora/coordinator/router.py` | Add task REST endpoints |

### DB Schema Changes

- New table: `task_graphs` (id, motion_id UNIQUE, created_at)
- New table: `tasks` (id, graph_id, motion_id, title, description, status,
  assigned_to, required_capabilities JSON, depends_on JSON, artifact_paths
  JSON, error_message, timestamps)
- New indices: `idx_tasks_graph`, `idx_tasks_motion`, `idx_tasks_status`,
  `idx_tasks_assigned`
- SCHEMA_VERSION: 5 → 6

### WebSocket Message Types Added

- `TASK_ASSIGNED` — coordinator → agent
- `TASK_STATUS` — agent → coordinator
- `TASK_COMPLETED` — agent → coordinator (alias for TASK_STATUS with
  status="done")
- `TASK_FAILED` — agent → coordinator (alias for TASK_STATUS with
  status="failed")
- `TASK_VERIFY` — coordinator → reviewer agent
- `TASK_ACCEPT_RESULT` — reviewer agent → coordinator

---

## Edge Cases & Error Handling

| Scenario | Handling |
|----------|----------|
| LLM call fails during generation | Fall back to heuristic generator |
| LLM returns invalid JSON | Retry once with stricter prompt; then heuristic |
| No agents with required capabilities | Task stays PENDING; logged as warning |
| Agent disconnects mid-task | Task stays RUNNING; heartbeat timeout → FAILED |
| Task assigned but agent never starts | No Phase 9 timeout for ASSIGNED→RUNNING; Phase 10 |
| DAG has cycles after generation | Validation rejects; fall back to heuristic |
| Motion closed with no action_items | No task graph generated (silent no-op) |
| Duplicate task graph generation | 409 Conflict returned |
| Reviewer rejects task | Task → REJECTED → PENDING; re-enters assignment pool |
| No reviewer agent available | Task stays DONE; logged as warning |
| Artifact paths point to non-existent files | Auto-verify fails; delegates to review |

---

## Testing Strategy

Unit tests for each module (follow existing test patterns in `tests/`):

```
tests/
  test_task_models.py       # TaskNode, TaskGraph serialization/validation
  test_task_storage.py      # CRUD operations against in-memory SQLite
  test_task_gen_heuristic.py # Heuristic generator output validation
  test_task_gen_llm.py      # LLM generator with mocked llm_call
  test_task_assign.py       # Capability matching, round-robin, load limits
  test_task_exec.py         # State machine transitions, invalid transitions
  test_task_verify.py       # Auto-verify logic, review delegation
```

---

## Dependencies on Other Phase 9 Sub-tasks

- **9.3 (Agent Protocol)**: Task assigner needs agent capabilities from the
  registry. The current `agents` table already has a `capabilities` field
  (JSON text). 9.3 enhances this with `agent_type`, `agent_token`, and
  `AgentConfig`. Task engine works with current agent model; 9.3 is additive.
- **9.4 (Rate Limiting)**: No direct dependency. Rate limiting is agent-side.
- **9.1 (Platform Independence)**: No direct dependency. Task engine works
  within the existing `agora/coordinator/` structure.

---

## What Phase 9.2 Does NOT Do

Per DESIGN-phase9.md B.5 constraints:
- No parallel task execution (sequential within graph)
- No task re-execution or automatic retry on failure
- No dynamic task insertion after graph generation
- Only one TaskGraph per motion
- No task timeout for ASSIGNED→RUNNING transition
- No test execution in verification (file existence only)
- No task priority or scheduling beyond round-robin
