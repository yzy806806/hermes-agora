# DESIGN-phase9-agent-protocol.md — Phase 9.3: Agent Registration Protocol Detailed Design

> Version: v0.9.0-draft | Date: 2026-06-10 | Author: planner
> Parent: docs/DESIGN-phase9.md Part C

## Background

Agora's current agent protocol is minimal: agents POST to `/agents/register`,
then open a WebSocket. There's no authentication, no heartbeat, no capability
tracking beyond a flat list of strings, and no distinction between agent types.

Phase 9.3 standardizes this. Per DESIGN-phase9.md Part C, this covers:

- **9.3a**: Update agent models (agent_type, model, max_concurrent_tasks,
  agent_token, is_approved)
- **9.3b**: Registration auth (token-based WS auth, AGORA_REQUIRE_APPROVAL,
  AGORA_ADMIN_TOKEN)
- **9.3c**: Heartbeat and capabilities (enhanced HEARTBEAT with load/active_tasks,
  capability match scoring, online/offline tracking)

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │      Agora Coordinator           │
                    │                                  │
                    │  POST /api/v1/agents/register    │
                    │  ┌─────────────────────────┐     │
                    │  │ agent_token generated,    │     │
                    │  │ is_approved set,          │     │
                    │  │ stored in agents table    │     │
                    │  └──────────┬────────────────┘     │
                    │             │                      │
                    │  GET /ws/{agent_id}?token=ag-xxx   │
                    │  ┌─────────────────────────┐     │
                    │  │ token validated,          │     │
                    │  │ is_approved checked,       │     │
                    │  │ ConnectionHub.connect()    │     │
                    │  └──────────┬────────────────┘     │
                    │             │                      │
                    │  HEARTBEAT every 30s              │
                    │  ┌─────────────────────────┐     │
                    │  │ load/active_tasks updated │     │
                    │  │ last_seen_at refreshed     │     │
                    │  │ offline detection via      │     │
                    │  │ heartbeat_timeout_timer    │     │
                    │  └────────────────────────────┘     │
                    └─────────────────────────────────────┘
```

---

## 9.3a: Agent Model Updates

### Files to Modify

```
agora/coordinator/models.py         # Add agent_type, agent_token, AgentConfig, new models
agora/coordinator/storage/schema.py # Add columns: agent_type, max_concurrent_tasks, agent_token, is_approved
agora/coordinator/storage/agents.py # Update CRUD: register with new fields, token lookup
agora/coordinator/router.py         # Update /agents/register response model
```

### Files NOT Changed

```
agora/coordinator/task_models.py    # No changes (tasks reference agent_id via FK)
agora/coordinator/ws.py             # No changes (ConnectionHub already works with agent dict)
agora/coordinator/ws_handlers.py    # Registration flow changes in 9.3b
```

### Data Model Updates (`models.py`)

**Add new enums:**

```python
class AgentType(str, Enum):
    """How the agent connects to Agora."""
    HERMES = "hermes"       # Hermes profile (current team)
    DOCKER = "docker"       # Docker container agent
    CLI = "cli"             # CLI agent (Codex, Claude Code, etc.)
    CUSTOM = "custom"       # Custom HTTP/WS agent (any language)


class AgentStatus(str, Enum):
    """Approval + online state combined."""
    PENDING = "pending"       # Waiting for admin approval
    APPROVED = "approved"     # Can connect and work
    REJECTED = "rejected"     # Admin rejected registration
    SUSPENDED = "suspended"   # Was approved, now blocked
```

**Update AgentRegisterRequest:**

```python
class AgentRegisterRequest(BaseModel):
    """Request body for agent registration (Phase 9.3)."""
    agent_id: str
    name: str
    capabilities: list[str] = Field(default_factory=list)

    # New fields (Phase 9.3)
    agent_type: AgentType = AgentType.HERMES
    model: str = "unknown"              # LLM model, e.g. "claude-sonnet-4"
    max_concurrent_tasks: int = 2       # How many tasks this agent can handle

    # Auth fields
    auth_token: str = ""                # Agent's own API key for re-auth

    # Removed fields (defunct in Phase 9):
    # - hermes_endpoint (no longer required; agents connect via WS, not Hermes endpoint)
```

**Update AgentInfo:**

```python
class AgentInfo(BaseModel):
    """Agent information stored in the system."""
    agent_id: str
    name: str
    model: str = ""

    # New fields (Phase 9.3)
    agent_type: AgentType = AgentType.HERMES
    max_concurrent_tasks: int = 2
    agent_token: str = ""               # Issued by coordinator on registration
    is_approved: bool = False           # True after admin approval
    approval_status: AgentStatus = AgentStatus.PENDING

    capabilities: list[str] = Field(default_factory=list)
    role: AgentRole = AgentRole.PARTICIPANT
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_online: bool = False
    last_seen: Optional[datetime] = None
    load: float = 0.0                   # Current load ratio (0.0-1.0), from HEARTBEAT
    active_tasks: list[str] = Field(default_factory=list)  # Task IDs, from HEARTBEAT

    # Removed fields (Phase 9):
    # - hermes_endpoint (defunct; only meaningful in Phase 1-8 plugin era)
```

**Add AgentConfig model (per DESIGN-phase9.md C.4):**

```python
class AgentConfig(BaseModel):
    """Per-agent runtime configuration, sent in WELCOME payload."""
    max_concurrent_tasks: int = 2
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 120
    tpm_limit: int = 10000                   # Tokens per minute
    allowed_discussion_roles: list[str] = Field(
        default_factory=lambda: ["participant"]
    )
    auto_accept_tasks: bool = False

class AgentRegistrationResponse(BaseModel):
    """Response for POST /api/v1/agents/register."""
    agent_id: str
    status: AgentStatus                     # "approved" or "pending"
    agent_token: str                        # Token for WS auth
    message: str = ""                       # Human-readable status
```

### DB Schema Changes (`schema.py`)

Bump `SCHEMA_VERSION` from 6 to 7. ALTER the `agents` table to add new columns:

```sql
-- Schema migration (version 6 → 7)
-- SQLite doesn't support DROP COLUMN, so we use ALTER TABLE ADD COLUMN
-- The hermes_endpoint column is kept (no DROP) to avoid data loss;
-- it's simply no longer used by new code.

-- Run these in order during migration:

-- 1. Add new columns (SQLite ALTER TABLE only supports ADD COLUMN)
ALTER TABLE agents ADD COLUMN agent_type TEXT DEFAULT 'hermes';
ALTER TABLE agents ADD COLUMN max_concurrent_tasks INTEGER DEFAULT 2;
ALTER TABLE agents ADD COLUMN agent_token TEXT DEFAULT '';
ALTER TABLE agents ADD COLUMN is_approved INTEGER DEFAULT 0;
ALTER TABLE agents ADD COLUMN approval_status TEXT DEFAULT 'pending';
ALTER TABLE agents ADD COLUMN load REAL DEFAULT 0.0;
ALTER TABLE agents ADD COLUMN active_tasks TEXT DEFAULT '[]';   -- JSON array
```

**Migration implementation in schema.py:**

```python
# schema.py — new migration for SCHEMA_VERSION 7

SCHEMA_VERSION = 7  # Bumped from 6

# Add to Migrations list
MIGRATION_6_TO_7 = [
    "ALTER TABLE agents ADD COLUMN agent_type TEXT DEFAULT 'hermes';",
    "ALTER TABLE agents ADD COLUMN max_concurrent_tasks INTEGER DEFAULT 2;",
    "ALTER TABLE agents ADD COLUMN agent_token TEXT DEFAULT '';",
    "ALTER TABLE agents ADD COLUMN is_approved INTEGER DEFAULT 0;",
    "ALTER TABLE agents ADD COLUMN approval_status TEXT DEFAULT 'pending';",
    "ALTER TABLE agents ADD COLUMN load REAL DEFAULT 0.0;",
    "ALTER TABLE agents ADD COLUMN active_tasks TEXT DEFAULT '[]';",
]
```

### Storage Methods Update (`storage/agents.py`)

**Updated register_agent() — Phase 9.3 signature:**

```python
async def register_agent(
    db: aiosqlite.Connection,
    agent_id: str,
    name: str,
    model: str = "unknown",
    capabilities: list[str] | None = None,
    role: str = "participant",
    # Phase 9.3 new params
    agent_type: str = "hermes",
    max_concurrent_tasks: int = 2,
    agent_token: str = "",          # Generated by coordinator
    is_approved: bool = False,      # Default False if AGORA_REQUIRE_APPROVAL
    approval_status: str = "pending",
) -> dict:
    """Register a new agent with Phase 9.3 fields. Returns dict."""
    caps_json = json.dumps(capabilities or [])
    active_tasks_json = json.dumps([])
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO agents
           (agent_id, name, model, capabilities, role,
            agent_type, max_concurrent_tasks, agent_token,
            is_approved, approval_status, load, active_tasks,
            registered_at, is_online)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
        [agent_id, name, model, caps_json, role,
         agent_type, max_concurrent_tasks, agent_token,
         1 if is_approved else 0, approval_status, 0.0, active_tasks_json, now],
    )
    await db.commit()
    return {
        "agent_id": agent_id,
        "name": name,
        "model": model,
        "capabilities": capabilities or [],
        "role": role,
        "agent_type": agent_type,
        "max_concurrent_tasks": max_concurrent_tasks,
        "agent_token": agent_token,
        "is_approved": 1 if is_approved else 0,
        "approval_status": approval_status,
        "load": 0.0,
        "active_tasks": "[]",
        "registered_at": now,
        "is_online": 1,
        "last_seen_at": None,
    }
```

**New function: lookup by token:**

```python
async def get_agent_by_token(
    db: aiosqlite.Connection, token: str
) -> Optional[dict]:
    """Look up agent by their agent_token (for WS auth)."""
    async with db.execute(
        "SELECT * FROM agents WHERE agent_token = ?", [token]
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None
```

**New function: update heartbeat info:**

```python
async def update_agent_heartbeat(
    db: aiosqlite.Connection,
    agent_id: str,
    load: float = 0.0,
    active_tasks: list[str] | None = None,
) -> None:
    """Update agent load and active tasks from HEARTBEAT."""
    active_json = json.dumps(active_tasks or [])
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE agents
           SET load = ?, active_tasks = ?, last_seen_at = ?, is_online = 1
           WHERE agent_id = ?""",
        [load, active_json, now, agent_id],
    )
    await db.commit()
```

**New function: set approval status:**

```python
async def set_agent_approval(
    db: aiosqlite.Connection,
    agent_id: str,
    is_approved: bool,
    approval_status: str,
) -> None:
    """Approve/reject/suspend an agent."""
    await db.execute(
        """UPDATE agents
           SET is_approved = ?, approval_status = ?
           WHERE agent_id = ?""",
        [1 if is_approved else 0, approval_status, agent_id],
    )
    await db.commit()
```

**New function: list offline agents (for heartbeat timeout detection):**

```python
async def list_stale_agents(
    db: aiosqlite.Connection,
    timeout_seconds: int = 120,
) -> list[dict]:
    """List agents whose last_seen is older than timeout_seconds.
    Used by heartbeat timeout checker to mark agents offline."""
    cutoff = (
        datetime.now(timezone.utc).isoformat()
        # Actually need to compute: now - timeout_seconds
        # We'll do the comparison in Python after fetching.
        # SQLite has no TIMESTAMP arithmetic built in.
    )
    async with db.execute(
        "SELECT * FROM agents WHERE is_online = 1"
    ) as cursor:
        rows = [dict(row) async for row in cursor]
    # Filter in Python
    stale = []
    for row in rows:
        last_seen = row.get("last_seen_at")
        if last_seen:
            try:
                seen_dt = datetime.fromisoformat(last_seen)
                elapsed = (datetime.now(timezone.utc) - seen_dt).total_seconds()
                if elapsed > timeout_seconds:
                    stale.append(row)
            except (ValueError, TypeError):
                pass
    return stale
```

### Storage class delegation methods

In `storage/storage.py`, add delegation methods matching the new agent storage functions:

```python
# In Storage class:
async def register_agent(self, **kwargs) -> dict:
    async with self._connection() as db:
        return await _agents.register_agent(db, **kwargs)

async def get_agent_by_token(self, token: str) -> Optional[dict]:
    async with self._connection() as db:
        return await _agents.get_agent_by_token(db, token)

async def update_agent_heartbeat(self, agent_id: str, load: float = 0.0,
                                  active_tasks: list[str] | None = None) -> None:
    async with self._connection() as db:
        return await _agents.update_agent_heartbeat(db, agent_id, load, active_tasks)

async def set_agent_approval(self, agent_id: str, is_approved: bool,
                              approval_status: str) -> None:
    async with self._connection() as db:
        return await _agents.set_agent_approval(db, agent_id, is_approved, approval_status)

async def list_stale_agents(self, timeout_seconds: int = 120) -> list[dict]:
    async with self._connection() as db:
        return await _agents.list_stale_agents(db, timeout_seconds)
```

### Key Design Decisions

1. **hermes_endpoint column kept but unused** — SQLite cannot DROP COLUMN
   without a full table rebuild. The column stays; new code ignores it.
   Phase 10 can do the cleanup if needed.
2. **agent_token is coordinator-generated UUID** — agent supplies an `auth_token`
   (its own key) on register; coordinator generates a separate `agent_token` for
   WS auth. This decouples agent credentials from coordinator credentials.
3. **load and active_tasks are updated per HEARTBEAT** — stored in DB for crash
   recovery. Not in-memory only.
4. **is_approved + approval_status are separate** — `is_approved` is a boolean for
   quick checks; `approval_status` is the full state machine (pending/approved/
   rejected/suspended).
5. **SCHEMA_VERSION bump to 7** — follows existing migration pattern.
6. **All JSON fields (capabilities, active_tasks) stored as TEXT** — consistent
   with existing patterns in schema.py.

---

## 9.3b: Registration Auth

### Files to Modify

```
agora/coordinator/config.py       # Add AGORA_REQUIRE_APPROVAL, AGORA_ADMIN_TOKEN
agora/coordinator/router.py       # Update /agents/register + new admin endpoints
agora/coordinator/ws_endpoint.py  # Add token validation on WS connect
agora/coordinator/ws_handlers.py  # Update handle_register to use new model
agora/coordinator/storage/schema.py # Migration for new columns (9.3a covers this)
```

### Files to Create

(None — all changes are modifications to existing files.)

### Config Settings (`config.py`)

Add these fields to the Settings class:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Phase 9.3: Agent registration auth
    require_approval: bool = False        # env: AGORA_REQUIRE_APPROVAL
    admin_token: str = ""                 # env: AGORA_ADMIN_TOKEN
                                          # Empty = admin auth disabled (dev mode)

    model_config = SettingsConfigDict(env_prefix="AGORA_")
```

Environment variables:
- `AGORA_REQUIRE_APPROVAL=true` — new agents need admin approval before connecting
- `AGORA_ADMIN_TOKEN=sk-admin-xxx` — required for admin endpoints (approve/reject/list agents)

### Registration Flow (updated `router.py`)

**POST /api/v1/agents/register** — Updated handler:

```python
# router.py — updated register_agent endpoint

import secrets

@router.post("/agents/register",
             response_model=AgentRegistrationResponse,
             status_code=201)
async def register_agent(request: AgentRegisterRequest) -> AgentRegistrationResponse:
    """Register a new agent. Returns agent_token for WS auth.

    If AGORA_REQUIRE_APPROVAL=true: agent is created with status=PENDING
    and cannot connect until approved.

    If AGORA_REQUIRE_APPROVAL=false (default): agent is auto-approved.
    """
    storage = _get_storage()
    existing = await storage.get_agent(request.agent_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Agent already registered")

    # Generate agent_token (random, unique)
    agent_token = f"ag-{secrets.token_hex(16)}"  # e.g. "ag-a1b2c3d4e5f6..."

    # Load config for approval logic
    from .config import settings
    require_approval = settings.require_approval

    is_approved = not require_approval
    approval_status = "approved" if is_approved else "pending"

    await storage.register_agent(
        agent_id=request.agent_id,
        name=request.name,
        model=request.model,
        capabilities=request.capabilities,
        role="participant",
        agent_type=request.agent_type.value,
        max_concurrent_tasks=request.max_concurrent_tasks,
        agent_token=agent_token,
        is_approved=is_approved,
        approval_status=approval_status,
    )

    message = (
        "Registration successful. You can now connect via WebSocket."
        if is_approved
        else "Registration pending approval. An admin must approve before you can connect."
    )

    return AgentRegistrationResponse(
        agent_id=request.agent_id,
        status=AgentStatus(approval_status),
        agent_token=agent_token,
        message=message,
    )
```

### Token-Based WebSocket Auth (`ws_endpoint.py`)

**Updated websocket_endpoint()** — validates token before accepting:

```python
# ws_endpoint.py — updated to validate agent_token on connect

async def websocket_endpoint(
    websocket: WebSocket,
    agent_id: str,
    token: str = "",            # NEW: query param
    tenant_id: str = "default",
) -> None:
    """FastAPI WebSocket endpoint at /ws/{agent_id}?token=ag-xxx.

    Phase 8.2: tenant_id query param for multi-tenancy.
    Phase 9.3: token query param for authentication.
    """
    hub = manager.get_hub(tenant_id)

    # Lazy-init deps (unchanged from current)
    if hub._storage is None and tenant_id != "default":
        storage_mgr = getattr(websocket.app.state, "storage_mgr", None)
        if storage_mgr is not None:
            from .state import StateMachine
            storage = await storage_mgr.get_tenant_storage(tenant_id)
            sm = StateMachine(storage)
            manager.set_tenant_deps(tenant_id, storage, sm)
            logger.info("Lazy-init deps for tenant %s", tenant_id)

    # Phase 9.3: Token validation BEFORE accepting the connection
    if hub._storage is not None:
        if token:
            # Validate token against stored agent_token
            agent = await hub._storage.get_agent(agent_id)
            if agent is None:
                await websocket.close(code=4004, reason="Agent not registered")
                return
            stored_token = agent.get("agent_token", "")
            if stored_token and stored_token != token:
                await websocket.close(code=4003, reason="Invalid token")
                return
            # Check approval
            if not agent.get("is_approved"):
                await websocket.close(
                    code=4005,
                    reason="Agent not approved. Wait for admin approval.",
                )
                return
        else:
            # No token provided — reject in production
            agent = await hub._storage.get_agent(agent_id)
            if agent is None:
                await websocket.close(code=4004, reason="Agent not registered")
                return
            # Allow no-token only for agents registered before Phase 9.3
            # (backward compat for migration period)
            if agent.get("agent_token"):
                await websocket.close(code=4003, reason="Token required")
                return

    # Now accept connection (rest is unchanged)
    if not await hub.connect(agent_id, websocket):
        return
    try:
        await hub.send(agent_id, {
            "type": MessageType.WELCOME,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "payload": {
                "config": {
                    "heartbeat_interval_seconds": 30,
                    "heartbeat_timeout_seconds": 120,
                    "tpm_limit": 10000,
                    "max_concurrent_tasks": agent.get("max_concurrent_tasks", 2)
                    if agent else 2,
                }
            },
        })
        while True:
            data = await websocket.receive_text()
            await _route_message(agent_id, data, hub)
    except Exception:
        pass
    finally:
        hub.disconnect(agent_id)
        await on_agent_disconnect(agent_id, hub)
```

### Updated handle_register (`ws_handlers.py`)

The old `handle_register` is invoked via `REGISTER` WS message (backward compat for
agents that connect first, then send REGISTER). Phase 9.3 updates it to use the new
fields:

```python
# ws_handlers.py — updated handle_register

async def handle_register(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process REGISTER: store agent info and mark online. Phase 9.3 updated."""
    name = payload.get("name", agent_id)
    model = payload.get("model", "unknown")
    caps = payload.get("capabilities", [])
    role = payload.get("role", "participant")
    agent_type = payload.get("agent_type", "hermes")
    max_concurrent = payload.get("max_concurrent_tasks", 2)

    # Generate token on-the-fly for WS-based registration
    import secrets
    agent_token = f"ag-{secrets.token_hex(16)}"

    await storage.register_agent(
        agent_id, name, model,
        capabilities=caps, role=role,
        agent_type=agent_type,
        max_concurrent_tasks=max_concurrent,
        agent_token=agent_token,
        is_approved=True,    # WS-register agents auto-approve for Phase 9
        approval_status="approved",
    )
    await storage.set_agent_online(agent_id, True)

    await mgr.send(agent_id, {
        "type": MessageType.WELCOME,
        "agent_id": agent_id,
        "payload": {
            "message": "Registration successful",
            "agent_token": agent_token,
            "config": {
                "heartbeat_interval_seconds": 30,
                "heartbeat_timeout_seconds": 120,
                "tpm_limit": 10000,
                "max_concurrent_tasks": max_concurrent,
            },
        },
    })
    logger.info("Agent %s registered via WebSocket", agent_id)
```

### Admin Endpoints (`router.py` additions)

Protected by `AGORA_ADMIN_TOKEN` (header: `Authorization: Bearer <token>`):

```python
# router.py — Admin endpoints

from fastapi import Header

ADMIN_TOKEN = settings.admin_token or ""  # Cache at module load


def _require_admin(authorization: str = Header("")) -> None:
    """Raise 401 if admin token not set or doesn't match."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=501, detail="Admin token not configured")
    token = authorization.removeprefix("Bearer ").strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/admin/agents", response_model=list[AgentInfo])
async def admin_list_agents(authorization: str = Header("")) -> list[AgentInfo]:
    """List all agents including approval status. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agents = await storage.list_agents()
    return [AgentInfo(**a) for a in agents]


@router.post("/admin/agents/{agent_id}/approve")
async def admin_approve_agent(
    agent_id: str,
    authorization: str = Header(""),
) -> dict:
    """Approve a pending agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, True, "approved")
    return {"agent_id": agent_id, "status": "approved"}


@router.post("/admin/agents/{agent_id}/reject")
async def admin_reject_agent(
    agent_id: str,
    authorization: str = Header(""),
) -> dict:
    """Reject a pending agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, False, "rejected")
    return {"agent_id": agent_id, "status": "rejected"}


@router.post("/admin/agents/{agent_id}/suspend")
async def admin_suspend_agent(
    agent_id: str,
    authorization: str = Header(""),
) -> dict:
    """Suspend a previously approved agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, False, "suspended")
    return {"agent_id": agent_id, "status": "suspended"}
```

### Key Design Decisions

1. **Token passed as query param** — `/ws/{agent_id}?token=ag-xxx`. Simpler than
   requiring HTTP headers on WebSocket upgrade (which browsers struggle with).
   Coordinators and agents can use headers too, but query param is the primary path.
2. **Backward compat: agents without token still connect** — during migration from
   Phase 8 to Phase 9, old agents may not have tokens. The WS endpoint only rejects
   if an agent HAS a stored token but didn't provide one.
3. **WS-level REGISTER still works** — agents can connect first and send REGISTER
   message. Phase 9.3 generates token on-the-fly in that path.
4. **Admin token is empty by default** — admin endpoints return 501 if unconfigured.
   This is "safe by default" for local dev.
5. **Agent 'auth_token' field on register is accepted but stored as-is** — Phase 9
   doesn't validate it. It's the agent's own key, not the coordinator's concern.
   Future phases may use it for agent-to-agent auth.

---

## 9.3c: Heartbeat and Capabilities

### Files to Modify

```
agora/coordinator/models.py       # Add HEARTBEAT to MessageType, define payload model
agora/coordinator/ws_endpoint.py  # Route HEARTBEAT messages
agora/coordinator/ws_handlers.py  # Add handle_heartbeat
agora/coordinator/main.py         # Start heartbeat timeout background task
```

### Files to Create

```
agora/coordinator/heartbeat.py    # Heartbeat timeout checker background task
```

### Message Type Addition (`models.py`)

```python
class MessageType(str, Enum):
    # ... existing types ...

    # Phase 9: Task execution + Agent protocol
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_STATUS = "TASK_STATUS"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_VERIFY = "TASK_VERIFY"
    TASK_ACCEPT_RESULT = "TASK_ACCEPT_RESULT"
    HEARTBEAT = "HEARTBEAT"           # Phase 9.3: periodic agent heartbeat
```

### Heartbeat Message Format

**Agent → Coordinator:**

```json
{
    "type": "HEARTBEAT",
    "agent_id": "dev-alpha",
    "motion_id": null,
    "payload": {
        "load": 0.5,
        "active_tasks": ["t-123", "t-456"],
        "capabilities": ["code", "test", "deploy"],
        "model": "claude-sonnet-4"
    }
}
```

Payload fields:
- `load` (float, 0.0-1.0): Current load ratio. 0.0 = idle, 1.0 = fully loaded.
- `active_tasks` (list[str]): Task IDs the agent is currently working on.
- `capabilities` (list[str], optional): Declare capabilities. Can update over time
  (e.g., after installing new tools).
- `model` (str, optional): Current model. Can change between heartbeats.

### Heartbeat Handler (`ws_handlers.py` addition)

```python
# ws_handlers.py — new handle_heartbeat

async def handle_heartbeat(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process HEARTBEAT: update load, active_tasks, capabilities, last_seen.

    Args:
        agent_id: Agent sending the heartbeat.
        payload: {load, active_tasks, capabilities?, model?}
        storage: Storage for persisting agent state.
        mgr: ConnectionManager (unused but kept for consistency).
    """
    load = float(payload.get("load", 0.0))
    active_tasks = payload.get("active_tasks", [])

    await storage.update_agent_heartbeat(
        agent_id, load=load, active_tasks=active_tasks,
    )

    # Optionally update capabilities if provided
    caps = payload.get("capabilities")
    if caps is not None:
        await storage.update_agent_capabilities(agent_id, caps)

    # Optionally update model if provided
    model = payload.get("model")
    if model is not None:
        await storage.update_agent_model(agent_id, model)

    # No response needed — heartbeat is fire-and-forget.
    # Coordinator uses this data for: assignment decisions, offline detection.
```

**New storage helpers for capability/model updates (in `storage/agents.py`):**

```python
async def update_agent_capabilities(
    db: aiosqlite.Connection, agent_id: str, capabilities: list[str],
) -> None:
    """Update agent capabilities from HEARTBEAT."""
    caps_json = json.dumps(capabilities)
    await db.execute(
        "UPDATE agents SET capabilities = ? WHERE agent_id = ?",
        [caps_json, agent_id],
    )
    await db.commit()

async def update_agent_model(
    db: aiosqlite.Connection, agent_id: str, model: str,
) -> None:
    """Update agent model from HEARTBEAT."""
    await db.execute(
        "UPDATE agents SET model = ? WHERE agent_id = ?",
        [model, agent_id],
    )
    await db.commit()
```

### Capability Match Scoring

The capability match scoring function defined in Phase 9.2 (DESIGN-phase9-task-engine.md,
Section 9.2c) is reused here. For completeness, here's the canonical implementation:

```python
# In agora/coordinator/task_assign.py (shared utility)
# OR in a new agora/coordinator/capability.py

def capability_match_score(
    agent_caps: list[str],
    required_caps: list[str],
) -> float:
    """Score how well an agent's capabilities match requirements.

    Returns 0.0 to 1.0.
    - Exact match of all required: 1.0
    - Partial match: len(intersection) / len(required)
    - Extra capabilities don't penalize
    - No requirements → 0.5 (neutral)
    """
    if not required_caps:
        return 0.5
    intersection = set(agent_caps) & set(required_caps)
    return len(intersection) / len(required_caps)
```

### Heartbeat Timeout Checker (`heartbeat.py`)

Background task that periodically checks for agents whose `last_seen_at` exceeds the
timeout threshold and marks them offline:

```python
"""Heartbeat timeout checker background task."""
from __future__ import annotations

import asyncio
import logging

from .storage import Storage
from .ws import manager
from .models import MessageType

logger = logging.getLogger(__name__)


async def heartbeat_timeout_checker(
    storage: Storage,
    interval: int = 15,              # Check every 15 seconds
    timeout: int = 120,              # Mark offline after 120s of no heartbeat
    tenant_id: str = "default",
) -> None:
    """Background task: check for stale agents and mark offline.

    Runs forever. Checks every `interval` seconds.
    If an agent hasn't sent HEARTBEAT in `timeout` seconds, mark offline
    and broadcast AGENT_OFFLINE.
    """
    while True:
        try:
            stale = await storage.list_stale_agents(timeout_seconds=timeout)
            for agent in stale:
                agent_id = agent["agent_id"]
                logger.warning(
                    "Agent %s heartbeat timeout (last seen %s), marking offline",
                    agent_id, agent.get("last_seen_at"),
                )
                await storage.set_agent_online(agent_id, False)

                hub = manager.get_hub(tenant_id)
                await hub.broadcast({
                    "type": MessageType.AGENT_OFFLINE,
                    "agent_id": agent_id,
                    "payload": {"reason": "heartbeat_timeout"},
                })
        except Exception:
            logger.exception("Heartbeat timeout checker error")
        await asyncio.sleep(interval)
```

### Integration into `main.py`

```python
# In main.py — app lifespan, start heartbeat checker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: existing init...
    # ... (storage init, router.init_deps, etc.)

    # Phase 9.3: Start heartbeat timeout checker as background task
    heartbeat_task = None
    if storage_manager.default_storage is not None:
        heartbeat_task = asyncio.create_task(
            heartbeat_timeout_checker(
                storage_manager.default_storage,
                interval=settings.heartbeat_interval_seconds or 30,
                timeout=settings.heartbeat_timeout_seconds or 120,
            )
        )
        logger.info("Heartbeat timeout checker started")

    yield

    # Shutdown: cancel heartbeat checker
    if heartbeat_task is not None:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("Heartbeat timeout checker stopped")
```

### WebSocket Routing (`ws_endpoint.py` addition)

Add HEARTBEAT dispatch in `_route_message()`:

```python
# In _route_message():
if msg_type == MessageType.HEARTBEAT:
    await handle_heartbeat(agent_id, payload, storage, hub)
```

### Online/Offline Tracking

The existing `on_agent_disconnect()` in `ws_endpoint.py` already handles immediate
offline marking on WebSocket disconnect. The heartbeat timeout checker handles the
case where the connection drops silently without proper close.

Combined tracking:
1. **WS disconnect** → `on_agent_disconnect()` marks offline immediately, broadcasts
   `AGENT_OFFLINE`.
2. **Heartbeat timeout** → `heartbeat_timeout_checker()` marks offline after
   `heartbeat_timeout_seconds` of no heartbeat, also broadcasts `AGENT_OFFLINE`.
3. **WS connect** → `ConnectionHub.connect()` marks online, sets `last_seen_at`.

This gives us both fast detection (case 1) and resilience against silent drops (case 2).

### Key Design Decisions

1. **Heartbeat is silent (no PONG response)** — fire-and-forget from agent.
   Coordinator updates DB and moves on. Reduces noise.
2. **Capabilities can change over time** — HEARTBEAT can include updated
   capabilities, model. Agent lifecycle: register with base capabilities,
   update via heartbeat.
3. **Timeout checker runs as asyncio background task in the coordinator process**
   — no separate process needed. Works within the existing FastAPI lifespan.
4. **Timeout intervals are configurable** — `AGORA_HEARTBEAT_INTERVAL_SECONDS`
   and `AGORA_HEARTBEAT_TIMEOUT_SECONDS` env vars.
5. **Capability match scoring is a utility function** — shared between task
   assigner (9.2c) and agent protocol (9.3c). Use the same implementation
   in both places.
6. **load is agent-reported, not coordinator-calculated** — agent knows its own
   state best. Coordinator uses it as a hint for assignment decisions.

---

## Implementation Order

For dev-merger, implement in this order:

1. **9.3a first** — schema migration + model updates + storage CRUD.
   Everything else depends on the new columns existing.
2. **9.3b second** — registration flow and WS auth. Depends on 9.3a
   (agent_token column must exist). Can be tested with curl.
3. **9.3c third** — heartbeat handler and timeout checker. Depends on 9.3a
   (load, active_tasks, last_seen_at columns must exist).

## Files Summary

| File | Action | Section |
|------|--------|---------|
| `agora/coordinator/models.py` | Modify | 9.3a: add AgentType, AgentStatus, update AgentRegisterRequest/AgentInfo, add AgentConfig/AgentRegistrationResponse; 9.3b: no changes; 9.3c: add HEARTBEAT to MessageType |
| `agora/coordinator/storage/schema.py` | Modify | 9.3a: bump SCHEMA_VERSION to 7, add migration SQL |
| `agora/coordinator/storage/agents.py` | Modify | 9.3a: update register_agent signature, add get_agent_by_token, update_agent_heartbeat, set_agent_approval, update_agent_capabilities, update_agent_model, list_stale_agents |
| `agora/coordinator/storage/storage.py` | Modify | 9.3a: add delegation methods for new agent storage functions |
| `agora/coordinator/config.py` | Modify | 9.3b: add require_approval, admin_token fields |
| `agora/coordinator/router.py` | Modify | 9.3b: update /agents/register, add admin endpoints |
| `agora/coordinator/ws_endpoint.py` | Modify | 9.3b: add token validation on connect; 9.3c: route HEARTBEAT |
| `agora/coordinator/ws_handlers.py` | Modify | 9.3b: update handle_register; 9.3c: add handle_heartbeat |
| `agora/coordinator/heartbeat.py` | Create | 9.3c: heartbeat_timeout_checker background task |
| `agora/coordinator/main.py` | Modify | 9.3c: start heartbeat checker in lifespan |

## API Endpoint Specs (New/Modified)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/agents/register` | None (public) | Register new agent, get token |
| WS | `/ws/{agent_id}?token=ag-xxx` | agent_token query param | Agent connection |
| GET | `/api/v1/admin/agents` | AGORA_ADMIN_TOKEN (Bearer) | List all agents (admin) |
| POST | `/api/v1/admin/agents/{id}/approve` | AGORA_ADMIN_TOKEN (Bearer) | Approve pending agent |
| POST | `/api/v1/admin/agents/{id}/reject` | AGORA_ADMIN_TOKEN (Bearer) | Reject pending agent |
| POST | `/api/v1/admin/agents/{id}/suspend` | AGORA_ADMIN_TOKEN (Bearer) | Suspend agent |

## WebSocket Message Types (New/Modified)

| Type | Direction | Payload | Purpose |
|------|-----------|---------|---------|
| HEARTBEAT | Agent → Coordinator | `{load, active_tasks, capabilities?, model?}` | Periodic health check |
| REGISTER | Agent → Coordinator | Updated with agent_type, max_concurrent_tasks | WS-based registration |
| WELCOME | Coordinator → Agent | Now includes `payload.config` with heartbeat_interval, tpm_limit | Config delivery |

## Capability Taxonomy (unchanged from DESIGN-phase9.md)

```python
CAPABILITIES = {
    "code":        "Write and modify code",
    "test":        "Write and run tests",
    "debug":       "Debug and fix issues",
    "refactor":    "Restructure existing code",
    "review":      "Review code and PRs",
    "security":    "Security audit",
    "docs":        "Write documentation",
    "design":      "Architecture and design",
    "planning":    "Task breakdown and planning",
    "research":    "Research and investigation",
    "deploy":      "Deploy to production",
    "release":     "Create releases",
    "monitor":     "Monitor and alert",
}
```

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| SCHEMA_VERSION bump to 7 may conflict if 9.2 merges first | Medium | Coordinate merge order: 9.2 first (uses v6), 9.3 bumps to v7. If 9.3 merges first, merge 9.2's migration as 7→8. |
| Old agents don't have agent_token | Low | Backward compat in ws_endpoint: agents with empty agent_token can still connect (Phase 9 migration grace period) |
| Heartbeat timeout checker competes with WS disconnect handler | Low | Both set `is_online=0` — idempotent. AGENT_OFFLINE may be broadcast twice if both fire; agents should handle duplicate. |
| Admin endpoints behind empty token = no security | Medium | Accept for Phase 9. Document that `AGORA_ADMIN_TOKEN` must be set before production use. |