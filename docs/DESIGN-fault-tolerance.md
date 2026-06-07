# Phase 5 Design: Fault Tolerance Mechanisms

> This document outlines the fault tolerance strategy for Hermes Agora Phase 5.

## Overview

Phase 1-4 have built a functional multi-agent discussion framework. Phase 5 adds resilience to handle:
- Agent connection drops and recovery
- Discussion timeout handling
- WebSocket reconnection
- Data consistency guarantees

## Priority: Critical

---

## 1. Agent Connection Monitoring

### 1.1 Heartbeat Protocol

**Current State:** No heartbeat mechanism exists. Agents can disconnect silently.

**Design:**
- Add `PING`/`PONG` message types (already present in models.py)
- Server sends periodic PING every 30 seconds to connected agents
- Agents must respond with PONG within 10 seconds
- After 3 missed PONGs, mark agent as OFFLINE

**Implementation:**
```python
# In ws.py ConnectionManager
class ConnectionManager:
    async def start_heartbeat(self):
        """Periodic heartbeat task."""
        while True:
            await asyncio.sleep(30)
            await self._send_heartbeats()
    
    async def _send_heartbeats(self):
        """Send PING to all connections, track response."""
        for agent_id in list(self.active_connections.keys()):
            try:
                await self.send(agent_id, {"type": "PING", "timestamp": time.time()})
                # Track in a pending_pings dict
                self.pending_pings[agent_id] = time.time()
            except Exception:
                pass
```

**Data Model:**
```python
# Add to storage/agents.py or new table
class AgentConnection:
    agent_id: str
    last_ping_sent: datetime
    last_pong_received: datetime
    missed_pings: int  # Reset to 0 on PONG
    status: AgentConnectionStatus  # ACTIVE, UNRESPONSIVE, OFFLINE
```

### 1.2 Agent Recovery

**Scenario:** Agent drops during a discussion round but reconnects.

**Design:**
1. Upon reconnection, agent sends `REGISTER` with same `agent_id`
2. Server checks if agent had active session (in DISCUSSING/VOTING motion)
3. If yes, replay missed messages since last seen
4. Agent resumes from where it left off

**Implementation:**
```python
async def handle_register(agent_id, payload, storage, manager):
    agent = await storage.get_agent(agent_id)
    if agent and agent.get("was_active"):
        # Get last seen position
        last_message_id = agent.get("last_message_id")
        missed = await storage.get_messages_since(motion_id, last_message_id)
        for msg in missed:
            await manager.send(agent_id, msg)
```

---

## 2. Discussion Timeout Handling

### 2.1 Round Timeout

**Current State:** Rounds progress based on agent speaking. No time limit.

**Design:**
- Per-motion `round_timeout_seconds` config (default: 300 = 5 minutes)
- Timer starts when motion enters DISCUSSING
- If round doesn't complete within timeout:
  1. Broadcast WARNING message at T-30s
  2. Auto-advance to next round or voting at timeout

**Implementation in state.py:**
```python
class StateMachine:
    async def check_round_timeout(self, motion_id: str):
        motion = await self.storage.get_motion(motion_id)
        if motion["status"] != MotionStatus.DISCUSSING:
            return
        
        elapsed = (datetime.now(datetime.UTC) - motion["round_started_at"]).seconds
        if elapsed > motion.get("round_timeout_seconds", 300):
            await self._auto_advance_round(motion_id)
    
    async def _auto_advance_round(self, motion_id: str):
        """Force advance to next round or voting."""
        # Logic to check if all rounds complete → voting
        # Or increment round and notify agents
```

### 2.2 Voting Timeout

**Design:**
- Motion enters VOTING with `voting_timeout_seconds` (default: 120s)
- After timeout, apply default behavior:
  - If quorum met (>50% registered agents voted): count existing votes
  - If quorum not met: motion closes with "insufficient_votes" decision
- Broadcast timeout notification to all agents

---

## 3. WebSocket Reconnection

### 3.1 Connection Manager Recovery

**Design:**
1. When WebSocket disconnects unexpectedly (not clean close):
   - Mark agent as "reconnecting" in memory (not immediately offline)
   - Wait up to 60 seconds for reconnection
2. On reconnect:
   - Validate via same `agent_id`
   - Restore session state from last known position

**Implementation:**
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.reconnecting: dict[str, float] = {}  # agent_id → disconnect_time
    
    def disconnect(self, agent_id: str):
        self.active_connections.pop(agent_id, None)
        self.reconnecting[agent_id] = time.time()
    
    async def reconnect(self, agent_id: str, websocket: WebSocket):
        if agent_id in self.reconnecting:
            elapsed = time.time() - self.reconnecting[agent_id]
            if elapsed < 60:  # Within grace period
                # Restore session
                del self.reconnecting[agent_id]
                self.active_connections[agent_id] = websocket
                return True
        return False
```

### 3.2 Message Delivery Guarantees

**Design:**
- Server-side message queue per agent (in-memory or Redis fallback)
- On reconnection, flush queued messages
- Implement "at-least-once" delivery for critical messages (VOTE_REQUEST)

---

## 4. Data Consistency

### 4.1 Transactional Storage

**Current State:** Uses SQLite. Some operations may leave inconsistent state on failure.

**Design:**
- Wrap multi-step operations in transactions
- Use SQLite's `BEGIN IMMEDIATE` for write operations
- Implement rollback handlers

**Example:**
```python
async def close_motion_with_votes(motion_id: str, votes: list):
    async with storage.db.transaction():
        await storage.update_motion_status(motion_id, "closed")
        await storage.save_votes(motion_id, votes)
        await storage.generate_result(motion_id)
```

### 4.2 Idempotency Keys

**Design:** For votes and messages, accept idempotency key to prevent duplicates.

```python
class VoteRequest(BaseModel):
    motion_id: str
    choice: str
    idempotency_key: str  # Client generates, server checks

async def handle_vote(request: VoteRequest):
    existing = await storage.get_by_idempotency_key(request.idempotency_key)
    if existing:
        return existing  # Return cached result
    # Process vote normally
```

---

## 5. Health Check Endpoint

**Design:** Add `/health` endpoint for load balancer and monitoring.

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(datetime.UTC).isoformat(),
        "active_agents": len(manager.active_connections),
        "active_motions": await storage.count_active_motions(),
    }
```

---

## Implementation Phases

| Phase | Feature | Priority |
|-------|---------|----------|
| 5.1 | Heartbeat protocol | P0 |
| 5.2 | Discussion timeout | P0 |
| 5.3 | WebSocket reconnection | P1 |
| 5.4 | Data consistency (transactions) | P1 |
| 5.5 | Health check endpoint | P2 |
| 5.6 | Agent recovery / replay | P2 |

---

## Files to Modify

- `coordinator/ws.py` - ConnectionManager heartbeat
- `coordinator/ws_endpoint.py` - Reconnection logic  
- `coordinator/state.py` - Timeout checks
- `coordinator/router.py` - Health endpoint
- `coordinator/storage/*.py` - Transactions, idempotency
- `coordinator/models.py` - New message types

---

## Testing Strategy

1. Unit test heartbeat ping/pong cycle
2. Unit test timeout auto-advance
3. Integration test reconnection with message replay
4. Integration test vote idempotency
5. Load test concurrent agent disconnects