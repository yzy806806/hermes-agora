# DESIGN-phase12.md — Phase 12: Multi-platform Agent Integration

> Version: v0.12.0-draft | Date: 2026-06-11 | Author: planner

## Background

Agora v0.11.0 is a fully functional multi-agent collaboration platform with
discussion, task execution (sequential + parallel DAG), agent registration
protocol, RBAC, plugin ecosystem, and a Web dashboard. 926 tests pass.

However, one critical gap remains: **all agent integrations are Hermes-only in
practice**. Despite the agent protocol supporting `AgentType` (hermes, docker,
cli, custom), only Hermes agents have ever been connected to Agora. The
ROADMAP's #1 future direction is "Multi-platform Agent integration — let
OpenClaw/PicoClaw and other non-Hermes agents connect to Agora."

The infrastructure is mostly in place (Phase 9.3 agent protocol, Phase 10.3
plugin hooks), but the concrete bridges to other platforms don't exist yet.

## Direction Evaluation

| Direction | Importance | Urgency | Feasibility | Complexity | Recommendation |
|---|---|---|---|---|---|
| Multi-platform Agent Bridges | ★★★★★ | ★★★★ | ★★★★ | Medium | **Phase 12 Core** |
| Agent SDK (Python client lib) | ★★★★★ | ★★★★ | ★★★★★ | Low | **Phase 12 Core** |
| Tool Bridge Adapter | ★★★★ | ★★★ | ★★★★ | Medium | **Phase 12 Core** |
| Full-auto Dev Loop E2E | ★★★★ | ★★★ | ★★★ | High | Defer to Phase 13 |
| Agent Self-evolution Support | ★★★★ | ★★★ | ★★★ | Medium | Phase 12 Scope |
| Dashboard Enhancement | ★★★ | ★★ | ★★★★ | Low | Defer to Phase 13 |
| Production Hardening | ★★★ | ★★★ | ★★★★ | Medium | Scattered in Phase 12 |

### Why Multi-platform First

1. **Platform value proposition** — Agora's pitch is "connect any agent". Without
   actual multi-platform bridges, it's just "Agora + Hermes".
2. **Low-hanging fruit** — The abstractions exist (AgentType, AgentProtocol,
   Plugin hooks). Building bridges is wiring, not greenfield.
3. **Unlocks ecosystem growth** — Each new platform integration is a new user
   base (OpenClaw users, Codex users, custom agent builders).
4. **Validates the protocol** — Writing concrete adapters forces us to harden
   the abstract protocol against real-world edge cases.

## Phase 12 Goals

### Primary: Agent SDK + Bridges

1. **Agora Agent SDK** — A lightweight Python library (`agora-agent-sdk`) that
   any agent runtime can import to connect to Agora. Replaces the current
   `agora.agent_client` module (which is tightly coupled to Agora internals).

2. **Hermes Bridge** — First-class bridge for Hermes agents. A Hermes plugin
   that auto-registers with Agora, maps Hermes tools ↔ Agora messages, and
   handles task execution lifecycle.

3. **Generic CLI Bridge** — A bridge for any CLI-based agent (Codex, Claude
   Code, OpenClaw, PicoClaw, etc.). Runs the CLI as a subprocess, intercepts
   tool calls, routes them through Agora.

4. **Docker/HTTP Bridge** — A bridge for containerized agents. Agent runs in a
   Docker container, communicates with Agora via HTTP/WS. Useful for
   language-agnostic agents (Node.js, Go, Rust, etc.).

### Secondary: Agent Self-evolution

5. **Session Persistence API** — Agora stores full session records (discussion
   turns, task executions, tool calls, errors) and provides a query API so
   agents can retrieve their own history for "experience accumulation".

6. **Project Artifact Storage** — A simple key-value store per project for
   agents to persist and retrieve artifacts (notes, findings, conventions, etc.)
   across sessions.

### Secondary: Production Hardening (scattered)

7. **E2E test fixes** — Fix 3 E2E WebSocket tests that need running server.
8. **Version assertion fix** — Update test_plugin_init.py version 0.10.0→0.11.0.

## Detailed Design

---

## Part A: Agora Agent SDK

### Motivation

The current `agora.agent_client.client.AgoraClient` works but has problems:

- Lives inside `agora` package — agents shouldn't need to install the full coordinator
- Tight coupling to FastAPI/test infrastructure
- No standard "agent lifecycle" concept — register → connect → receive tasks → execute → report
- Rate limiting is bolted on client side

The SDK should be a **separate pip package** (`agora-agent-sdk`) that can be
installed standalone. It provides:

### SDK Architecture

```
agora-agent-sdk
├── __init__.py          # Public API surface
├── client.py            # AgoraAgentClient — main class
├── protocol.py          # WS message enums, models (no FastAPI deps)
├── bridge.py            # AbstractBridge ABC — base class for platform bridges
├── session.py           # SessionStore — agent-side log persistence
└── tool_adapter.py      # ToolAdapter — converts tool calls between formats
```

### AgoraAgentClient

```python
class AgoraAgentClient:
    """SDK client for an agent to connect to Agora Coordinator.

    Replaces the monolithic AgoraClient in agora.agent_client.
    Designed to work standalone without installing agora package.
    """

    def __init__(self, config: AgentConfig):
        """
        config fields:
          - coordinator_url: str       # e.g. "http://localhost:8000"
          - agent_id: str
          - agent_name: str
          - agent_type: str            # "hermes", "cli", "docker", "custom"
          - capabilities: list[str]
          - model: str
          - agent_token: str | None    # from registration
          - heartbeat_interval: int    # default 30
          - max_retries: int           # default 3
        """

    # -- Lifecycle --
    async def register(self) -> RegistrationResult
    async def connect(self) -> None          # opens WS, sends HEARTBEAT loop
    async def disconnect(self) -> None
    async def run(self) -> None              # blocking run loop

    # -- Discussion --
    async def create_motion(title, desc, ...) -> MotionResult
    async def speak(motion_id, content, ...) -> SpeechResult
    async def vote(motion_id, choice, ...) -> VoteResult

    # -- Task Execution --
    async def report_task_start(task_id) -> None
    async def report_task_progress(task_id, pct) -> None
    async def report_task_complete(task_id, artifacts) -> None
    async def report_task_failed(task_id, error) -> None

    # -- Session --
    async def query_sessions(filter) -> list[SessionRecord]
    async def get_artifact(key) -> bytes | None
    async def put_artifact(key, value) -> None
```

### AbstractBridge ABC

```python
class AbstractBridge(ABC):
    """Bridge between an agent runtime and AgoraAgentClient.

    Each platform (Hermes, CLI tools, Docker) implements this ABC.
    The bridge translates platform-specific tool calls into Agora
    WS messages, and vice versa.
    """

    client: AgoraAgentClient

    @abstractmethod
    async def on_task_assigned(self, task: TaskNode) -> None:
        """Called when a TASK_ASSIGNED message arrives.
        Should start executing the task on the platform."""
        ...

    @abstractmethod
    async def on_discussion_message(self, motion_id: str,
                                     content: str) -> None:
        """Called when a discussion message arrives (e.g. SPEECH_ADDED).
        The agent's turn to speak in a discussion."""
        ...

    @abstractmethod
    async def on_devils_advocate(self, motion_id: str, topic: str) -> str:
        """Called when coordinator requests a devil's advocate response.
        Should return the agent's counter-argument."""
        ...

    async def start(self) -> None:
        """Default lifecycle: register, connect, run."""
        await self.client.register()
        await self.client.connect()
        await self.client.run()

    async def stop(self) -> None:
        await self.client.disconnect()
```

### The run() Loop

```python
async def run(self):
    """Main event loop. Receives WS messages and dispatches to bridge."""
    while self._connected:
        msg = await self._ws.receive()    # WS message
        msg_type = msg.get("type")

        if msg_type == "TASK_ASSIGNED":
            task = TaskNode(**msg["payload"])
            await self.bridge.on_task_assigned(task)
        elif msg_type == "SPEECH_ADDED":
            await self.bridge.on_discussion_message(
                msg["payload"]["motion_id"],
                msg["payload"]["content"],
            )
        elif msg_type == "DEVILS_ADVOCATE_REQUEST":
            response = await self.bridge.on_devils_advocate(
                msg["payload"]["motion_id"],
                msg["payload"]["topic"],
            )
            await self._ws.send({
                "type": "DEVILS_ADVOCATE_RESPONSE",
                "payload": {"content": response},
            })
        elif msg_type == "HEARTBEAT_ACK":
            self._last_ack = time.time()
        elif msg_type == "WELCOME":
            self._agent_config = msg["payload"]["config"]
```

### Key Differences from Current AgoraClient

| Aspect | Current (agora.agent_client) | SDK |
|--------|-----|-----|
| Dependencies | Full agora, httpx, pydantic | Standalone, only httpx + pydantic |
| Location | Inside agora package | Separate pip package |
| Tool mapping | Hardcoded 6 Hermes tools | Abstract bridge pattern |
| Lifecycle | Manual register+connect | run() event loop |
| Error handling | Dict returns | Proper exceptions |
| Session | None | Built-in session store |
| Rate limit | Client tracker only | SDK handled, transparent |

### Files to Create

```
agora-agent-sdk/
├── pyproject.toml
├── README.md
├── src/agora_agent_sdk/
│   ├── __init__.py
│   ├── client.py          # ~150 lines
│   ├── protocol.py        # ~100 lines (copy MessageType enum, WS message models)
│   ├── bridge.py           # ~80 lines (AbstractBridge ABC)
│   ├── session.py          # ~120 lines (SessionStore)
│   └── tool_adapter.py     # ~80 lines (ToolAdapter)
└── tests/
    ├── test_client.py
    ├── test_bridge.py
    └── test_session.py
```

### Protocol Models (protocol.py)

These are copies of the coordinator-side models, **without FastAPI deps**:

```python
class MessageType(str, Enum):
    # Subset needed by agents:
    REGISTER = "REGISTER"
    SPEAK = "SPEAK"
    SPEECH_ADDED = "SPEECH_ADDED"
    VOTE = "VOTE"
    VOTE_CONFIRMED = "VOTE_CONFIRMED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STATUS = "TASK_STATUS"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    WELCOME = "WELCOME"
    ERROR = "ERROR"
    # ... etc
```

**Decision**: We share the MessageType enum between coordinator and SDK. A
single source of truth file (`agora/protocol/__init__.py`) is symlinked or
copied at build time. This avoids duplication drift.

---

## Part B: Hermes Bridge

### Goal

Make the existing 5 Hermes profile team (maintainer/planner/dev-merger/
reviewer/releaser) connect to Agora **through the SDK**, not through cron +
kanban.

### Architecture

```
┌─────────────────────┐       ┌──────────────────┐       ┌──────────────┐
│  Hermes Profile      │       │  Hermes Bridge    │       │  Agora       │
│  (maintainer, etc.)  │◄─────►│  (Python plugin)  │◄─────►│  Coordinator │
│                       │  IPC  │                    │  WS   │              │
│  cron scheduler       │       │  AgoraAgentClient  │       │  :8000       │
│  ──────────────────  │       │  + HermesAdapter   │       │              │
│  - reads Agora WS    │       │  - maps kanban→task │       │              │
│  - writes memory     │       │  - maps tools→WS    │       │              │
│  - uses skills       │       │  - session persist  │       │              │
└─────────────────────┘       └──────────────────┘       └──────────────┘
```

### HermesAdapter (implements AbstractBridge)

```python
class HermesAdapter(AbstractBridge):
    """Bridge for Hermes profiles. Translates between Hermes
    internal mechanisms (kanban, cron, tools) and Agora WS messages."""

    def __init__(self, profile_name: str):
        self.profile = profile_name

    async def on_task_assigned(self, task: TaskNode):
        """Convert TASK_ASSIGNED → Hermes kanban task."""
        # Use `hermes kanban create` via subprocess
        # Map task fields to kanban task fields
        # The hermes profile's cron picks it up and executes

    async def on_discussion_message(self, motion_id, content):
        """Convert discussion message → Hermes agent prompt."""
        # Route to the profile's stdin or a shared state file
        # The cron job reads it and generates a response
```

**Decision**: The Hermes Bridge is a **daemon process** that runs alongside
Agora. It:
1. Registers all 5 profiles as agents
2. Listens to Agora WS for task assignments and discussion messages
3. Translates them into Hermes kanban tasks or prompts
4. Polls Hermes for task completion and reports back to Agora

**Alternative considered**: Modify Hermes cron jobs to directly call
AgoraAgentClient. But this requires changing every profile's cron script and
tightly couples Hermes to Agora. The bridge approach keeps Hermes unchanged.

### Implementation Plan

1. Create `hermes_bridge/` package (separate from agora and agora-agent-sdk)
2. Uses `agora-agent-sdk` for Agora communication
3. Uses `hermes kanban` CLI for Hermes interaction
4. Runs as a systemd service or Docker container alongside Agora

---

## Part C: Generic CLI Bridge

### Goal

Connect any CLI-based agent (Codex, Claude Code, OpenClaw, PicoClaw, etc.)
to Agora **without modifying the agent**.

### Architecture

```
┌──────────────────┐       ┌───────────────────┐       ┌──────────────┐
│  CLI Agent        │       │  CLI Bridge        │       │  Agora       │
│  (Codex, etc.)    │◄─────►│  (Python daemon)   │◄─────►│  Coordinator │
│                    │ stdin │                    │  WS   │              │
│  $ codex chat      │ stdout│  ToolInterceptor   │       │  :8000       │
│  ────────────────  │       │  → intercepts tool  │       │              │
│  - read files      │       │    calls           │       │              │
│  - write files     │       │  → routes to Agora  │       │              │
│  - run commands    │       │  → returns results  │       │              │
│  - web searches    │       │                    │       │              │
└──────────────────┘       └───────────────────┘       └──────────────┘
```

### How It Works

The CLI Bridge spawns the agent as a subprocess with a PTY (pseudo-terminal).
It intercepts all tool calls the agent makes and routes them through Agora's
standard protocol:

```
1. Agent runs `codex chat --model claude-sonnet-4`
2. Codex decides to read a file → emits a tool call
3. CLI Bridge intercepts the tool call
4. CLI Bridge checks: is this tool call allowed? (RBAC)
5. If file read: execute locally, return result
6. If external API: route through Agora plugin hooks
7. If task-related: report progress to Agora coordinator
```

### ToolAdapter

```python
class ToolAdapter:
    """Translates between different agent tool call formats.

    Each CLI agent has its own tool call format:
    - Codex: JSON in stdout
    - Claude Code: MCP protocol over stdio
    - OpenClaw: custom format
    - PicoClaw: TBD

    ToolAdapter normalizes them into Agora's standard tool call format.
    """

    def parse_tool_call(self, agent_type: str, raw: str) -> ToolCall:
        """Parse a tool call from the agent's raw output."""

    def format_tool_result(self, agent_type: str,
                            result: ToolResult) -> str:
        """Format a tool result for the agent to consume."""
```

### Supported CLI Agents (initial set)

| Agent | Status | Bridge implementation |
|---|---|---|
| Codex (OpenAI) | CLI available | PTY subprocess + stdout parser |
| Claude Code | CLI available | PTY subprocess + MCP protocol |
| OpenClaw | CLI available | PTY subprocess + custom parser |
| PicoClaw | Needs research | PTY subprocess + TBD |

### Files to Create

```
cli_bridge/
├── pyproject.toml
├── README.md
├── src/cli_bridge/
│   ├── __init__.py
│   ├── main.py              # Entry point, subprocess management
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py          # Base adapter ABC
│   │   ├── codex_adapter.py
│   │   ├── claude_adapter.py
│   │   ├── openclaw_adapter.py
│   │   └── picoclaw_adapter.py
│   └── sandbox.py           # Optional: containerize CLI agent
└── tests/
    └── test_adapters.py
```

---

## Part D: Docker / HTTP Bridge

### Goal

Let agents written in any language connect to Agora. The agent runs in a Docker
container and communicates via HTTP REST + WebSocket.

### Architecture

```
┌──────────────────┐       ┌───────────────────┐       ┌──────────────┐
│  Docker Agent     │       │  Agora             │       │              │
│  (any language)   │◄─────►│  Coordinator       │       │              │
│                    │ HTTP  │                    │       │              │
│  /docker/agent1   │  WS   │  :8000             │       │              │
│  ────────────────  │       │                    │       │              │
│  - Node.js agent   │       │  Docker Bridge     │       │              │
│  - Go agent        │       │  (built into       │       │              │
│  - Rust agent      │       │   coordinator)     │       │              │
│  - bun agent       │       │                    │       │              │
└──────────────────┘       └───────────────────┘       └──────────────┘
```

### How It Works

This is **the simplest bridge** because Docker agents already speak HTTP/WS,
which is Agora's native protocol. No translation needed.

1. Agent developer writes `Dockerfile` that includes `agora-agent-sdk` (or a
   language-specific port of the protocol)
2. Agent starts → calls `POST /api/v1/agents/register`
3. Agent opens `WS /ws/{agent_id}?token={token}`
4. Agent follows the standard WS message protocol

The "bridge" here is just **documentation + examples + SDK ports**:

### Language-Specific SDK Ports

| Language | Priority | Notes |
|---|---|---|
| Python | **P0 — Phase 12** | Full SDK (Part A) |
| Node.js | **P0 — Phase 12** | JavaScript port, npm package |
| Go | P1 — Phase 13 | Popular for CLI tools |
| Rust | P1 — Phase 13 | Performance-critical agents |
| Shell/Bash | P2 — Later | Lightweight, curl + websocat |

**Decision**: Only Python and Node.js SDKs in Phase 12. Others deferred.

### Node.js SDK

```javascript
// @agora/agent-sdk — npm package
import { AgoraAgentClient } from '@agora/agent-sdk';

const client = new AgoraAgentClient({
    coordinatorUrl: process.env.AGORA_URL,
    agentId: 'node-agent-1',
    agentName: 'My Node Agent',
    capabilities: ['code-review', 'testing'],
    agentType: 'docker',
    model: 'gpt-4',
});

await client.register();
await client.connect();

client.on('task_assigned', async (task) => {
    // Execute task
    await client.reportTaskStart(task.id);
    // ... do work ...
    await client.reportTaskComplete(task.id, { files: ['output.txt'] });
});

await client.run();
```

---

## Part E: Agent Self-evolution Support (Session Persistence)

### Goal

Enable agents to accumulate experience across sessions. Per ROADMAP:
"Agora coordinator 不替代 agent 的 skill/memory 机制——那是 agent 自己的事。
Agora 只需要提供 session 记录和检索 API。"

### Session Storage Model

```python
class SessionRecord(BaseModel):
    """A single session for an agent. Stored in Agora DB."""
    id: str                       # ulid
    agent_id: str
    project_id: str               # which project this session belongs to
    session_type: str             # "discussion" | "task_execution" | "observation"
    started_at: datetime
    ended_at: datetime | None
    input_messages: list[dict]    # Messages received by agent
    output_messages: list[dict]   # Messages sent by agent
    tool_calls: list[dict]        # Tool invocations (name, args, result)
    errors: list[dict]            # Error events
    outcome: str                  # "success" | "failure" | "timeout" | "cancelled"
    metadata: dict                # Agent-defined tags, notes, etc.
```

### API Endpoints

```
POST   /api/v1/sessions                        # Record a session
GET    /api/v1/sessions?agent_id=X&project_id=Y # Query sessions
GET    /api/v1/sessions/{id}                    # Get full session detail
POST   /api/v1/sessions/{id}/notes              # Agent adds notes to session

GET    /api/v1/projects/{project_id}/artifacts/{key}  # Get artifact
PUT    /api/v1/projects/{project_id}/artifacts/{key}  # Store artifact
DELETE /api/v1/projects/{project_id}/artifacts/{key}  # Delete artifact
```

### Artifact Storage

Simple key-value store per project. Backed by SQLite BLOB column (initially) or
filesystem (for large artifacts).

```sql
-- New table: project_artifacts
CREATE TABLE project_artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value BLOB,
    content_type TEXT DEFAULT 'application/octet-stream',
    created_by TEXT NOT NULL,    -- agent_id
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(project_id, key)
);
```

### How Agents Use Sessions

An agent, before starting a new task, does:

```python
# Agent queries its own history
sessions = await client.query_sessions(
    agent_id="my-agent",
    project_id="agora-project",
    limit=10,
)

# Extract patterns: what worked, what didn't
for s in sessions:
    if s.outcome == "failure":
        # Learn from errors
        pass

# Read project conventions
conventions = await client.get_artifact("coding_conventions")
```

This is not Agora telling the agent what to do — it's the agent choosing
what to learn from its own history. Agora just provides the storage and
query API.

### Implementation

- **storage/sessions.py** — new file, CRUD for session records
- **storage/artifacts.py** — new file, CRUD for project artifacts
- **schema.py** — migration for new tables (SCHEMA_VERSION 8→9)
- **router.py** — new API routes (behind RBAC: agent can read own, admin can read all)
- **agora-agent-sdk** — adds `query_sessions()` / `get_artifact()` / `put_artifact()`

---

## Part F: Production Hardening (Scattered)

Small fixes to do alongside Phase 12:

| Item | Issue | Fix |
|---|---|---|
| E2E WS tests | 3 tests need running server | Add integration test with subprocess fixture |
| Version assertion | test_plugin_init.py expects 0.10.0 | Update to 0.11.0 |
| test count | 923/926 pass (3 known E2E skips) | Resolve E2E tests |

## Sub-task Breakdown

```
Phase 12: Multi-platform Agent Integration
├── 12.1 Agent SDK (Python)
│   ├── 12.1a: Create agora-agent-sdk package structure
│   ├── 12.1b: Implement AgoraAgentClient + protocol models
│   ├── 12.1c: Implement AbstractBridge + run() loop
│   ├── 12.1d: Implement SessionStore in SDK
│   ├── 12.1e: Write SDK tests (mock coordinator)
│   └── 12.1f: SDK documentation + examples
│
├── 12.2 Hermes Bridge
│   ├── 12.2a: Design HermesAdapter (kanban task mapping)
│   ├── 12.2b: Implement Hermes Bridge daemon
│   └── 12.2c: Test with real Hermes profiles
│
├── 12.3 CLI Bridge
│   ├── 12.3a: Implement PTY subprocess manager
│   ├── 12.3b: Codex adapter
│   ├── 12.3c: Claude Code adapter
│   ├── 12.3d: OpenClaw adapter
│   └── 12.3e: CLI Bridge tests
│
├── 12.4 Docker/HTTP Bridge (Node.js SDK)
│   ├── 12.4a: Node.js SDK (@agora/agent-sdk npm package)
│   ├── 12.4b: Docker agent example + Dockerfile template
│   └── 12.4c: Documentation
│
├── 12.5 Agent Self-evolution
│   ├── 12.5a: Session storage model + schema migration
│   ├── 12.5b: Session CRUD API endpoints
│   ├── 12.5c: Project artifact storage + API
│   └── 12.5d: SDK integration (query_sessions, artifacts)
│
├── 12.6 Production Hardening
│   ├── 12.6a: Fix E2E WebSocket tests (subprocess fixture)
│   └── 12.6b: Fix version assertion
│
└── 12.7 Integration + Documentation
    ├── 12.7a: Update ARCHITECTURE.md for Phase 12
    ├── 12.7b: Update API.md for new endpoints
    ├── 12.7c: Update ROADMAP.md
    └── 12.7d: CHANGELOG.md v0.12.0 entry
```

### Task Dependency Graph

```
12.1a ──► 12.1b ──► 12.1c ──► 12.1d ──► 12.1e ──► 12.1f
                │
                ├──► 12.2a ──► 12.2b ──► 12.2c
                ├──► 12.3a ──► 12.3b ──► 12.3c ──► 12.3d ──► 12.3e
                └──► 12.4a ──► 12.4b ──► 12.4c

12.5a ──► 12.5b ──► 12.5c ──► 12.5d
                              (12.5d depends on 12.1d for SDK sync)

12.6a ──► 12.6b

12.7a ──► 12.7b ──► 12.7c ──► 12.7d
```

## Estimated Timeline

| Part | Tasks | Estimated Days | Parallelizable |
|---|---|---|---|
| 12.1 Agent SDK | 6 tasks | 4-5 days | No (sequential deps) |
| 12.2 Hermes Bridge | 3 tasks | 3-4 days | After 12.1 |
| 12.3 CLI Bridge | 5 tasks | 5-7 days | After 12.1 |
| 12.4 Node.js SDK | 3 tasks | 3-4 days | After 12.1 |
| 12.5 Self-evolution | 4 tasks | 3-4 days | After 12.1 |
| 12.6 Hardening | 2 tasks | 1-2 days | Anytime |
| 12.7 Docs | 4 tasks | 1-2 days | End |

**Total**: ~20-28 days sequential, ~12-15 days with parallel execution (12.2,
12.3, 12.4, 12.5 can run in parallel after 12.1 completes).

## What We're NOT Doing in Phase 12

- **Full-auto development loop E2E** — Connecting all pieces end-to-end requires
  the bridges to be stable first. Deferred to Phase 13.
- **Dashboard enhancement** — Real-time WS push, charts, notifications. Deferred
  to Phase 13.
- **Agent protocol v2** — The current protocol is sufficient. Deferred until we
  have real multi-platform experience to inform what v2 needs.
- **Multi-tenant production deployment** — Docker Compose with multi-tenant
  support. Deferred to Phase 13+.
- **Go/Rust SDKs** — Only Python and Node.js in Phase 12.
- **PicoClaw adapter** — Needs research first. Included as placeholder in CLI
  bridge, but not required for Phase 12 completion.

## Design Decisions Summary

1. **Separate SDK package (`agora-agent-sdk`)** — Clean separation from
   coordinator. Agents don't need to install the full Agora package.

2. **Hermes Bridge as daemon, not modified cron** — Keeps Hermes unchanged.
   Bridge translates between kanban and Agora WS messages.

3. **CLI Bridge uses PTY subprocess** — No modification needed to CLI agents.
   ToolAdapter normalizes different tool call formats.

4. **Node.js SDK as npm package** — Unlocks the JS/TS ecosystem without
   requiring Python knowledge.

5. **Session persistence in Agora, not in agent** — Agora stores records; agents
   query them. Follows ROADMAP directive: "Agora 不替代 agent 的 memory 机制".

6. **Artifact storage as simple KV** — Not a full document store. Enough for
   conventions, notes, findings. Larger artifacts stay in git/project.

7. **No agent protocol v2** — Phase 9.3 protocol is proven and sufficient. Wait
   for real multi-platform experience before revising.
