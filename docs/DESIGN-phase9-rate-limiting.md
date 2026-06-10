# DESIGN-phase9-rate-limiting.md — Phase 9.4: API Rate Limiting (Token Bucket)

> Version: v0.9.0-draft | Date: 2026-06-10 | Author: planner
> Parent: docs/DESIGN-phase9.md Part D

## Background

Agora agents make LLM API calls (to Claude, GPT, etc.) during task execution.
Without rate limiting, a misconfigured or runaway agent could exhaust API credits
in minutes. Phase 9.4 implements per-agent TPM (tokens per minute) limits using
the token bucket algorithm.

Key design decision: **Agora does not proxy LLM calls.** Agents call LLM APIs
directly. Rate limiting is therefore a **dual enforcement** model:

1. **Coordinator-side tracking** — Agora tracks usage and provides rate limit
   status to agents and operators
2. **Client-side pre-check** — The `AgoraClient` library checks its local bucket
   before making LLM calls, avoiding wasted API requests

This mirrors how Kubernetes resource limits work: the API server stores the
limit, the kubelet enforces it locally.

## Architecture

```
                    ┌──────────────────────────────────────┐
                    │        Agora Coordinator              │
                    │                                       │
                    │  AgentConfig.tpm_limit = 10000        │
                    │  AgentConfig.tpm_burst = 1.5x         │
                    │                                       │
                    │  ┌──────────────────────────────┐     │
                    │  │  TokenRateLimiter (in-memory) │     │
                    │  │  - per-agent TokenBucket      │     │
                    │  │  - periodic flush to DB       │     │
                    │  └──────────┬───────────────────┘     │
                    │             │                          │
                    │  GET /api/v1/agents/{id}/rate-limit    │
                    │  POST /api/v1/agents/{id}/rate-limit   │
                    │       /report                          │
                    │                                       │
                    │  WS: RATE_LIMIT_WARNING (80% used)    │
                    │  WS: RATE_LIMITED (100% used)          │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────┴───────────────────────┐
                    │         AgoraClient (agent side)      │
                    │                                       │
                    │  ┌──────────────────────────────┐     │
                    │  │  RateLimitTracker (local)     │     │
                    │  │  - syncs config from WELCOME  │     │
                    │  │  - pre-checks before LLM call │     │
                    │  │  - reports usage after call   │     │
                    │  └──────────────────────────────┘     │
                    └──────────────────────────────────────┘
```

## 1. Token Bucket Algorithm

### 1.1 Core Concept

A token bucket has:
- **capacity** (max tokens): `tpm_limit * burst_factor` (default burst = 1.5x)
- **tokens** (current count): starts at capacity
- **refill_rate** (tokens/second): `tpm_limit / 60`
- **last_refill** (timestamp): last time tokens were added

On each `consume(n)`:
1. Refill: `tokens = min(capacity, tokens + (now - last_refill) * refill_rate)`
2. If `tokens >= n`: deduct n, return True
3. Else: return False (rate limited)

This is superior to the existing sliding window counter (in `rate_limiter.py`)
because:
- Token bucket allows **bursts** — an agent can use tokens faster than the
  steady rate, up to the burst capacity, then must wait
- Sliding window is all-or-nothing per minute — bucket is smooth
- Token bucket is the industry standard (AWS API Gateway, Stripe, etc.)

### 1.2 Implementation

```python
import time
import threading
from dataclasses import dataclass


@dataclass
class TokenBucket:
    """Thread-safe token bucket for TPM rate limiting."""

    capacity: float          # Max tokens (tpm_limit * burst_factor)
    refill_rate: float       # Tokens per second (tpm_limit / 60)
    tokens: float = 0.0
    last_refill: float = 0.0
    _lock: threading.Lock | None = None

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, tokens: int) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    @property
    def available(self) -> float:
        """Current available tokens (read-only, no side effects)."""
        with self._lock:
            self._refill()
            return self.tokens

    @property
    def usage_ratio(self) -> float:
        """0.0 (empty) to 1.0 (full)."""
        return 1.0 - (self.available / self.capacity) if self.capacity > 0 else 0.0

    def time_until_available(self, needed: int) -> float:
        """Seconds until `needed` tokens become available."""
        avail = self.available
        if avail >= needed:
            return 0.0
        return (needed - avail) / self.refill_rate if self.refill_rate > 0 else float("inf")
```

### 1.3 Burst Allowance

Default burst factor: 1.5x. Rationale:

- A 10,000 TPM agent starts with 15,000 tokens in the bucket
- It can make one large call (e.g., 12,000 tokens) immediately
- Then it must wait for refill: 12,000 / (10,000/60) = 72 seconds
- Without burst, it could only make a 10,000 token call, then wait 60 seconds

Burst is configurable per agent via `AgentConfig.tpm_burst_factor` (default 1.5,
range 1.0-3.0).

## 2. Coordinator-Side Tracking

### 2.1 TokenRateLimiter (extends existing RateLimiter)

The existing `RateLimiter` handles action-based rate limiting (speak, vote).
The new `TokenRateLimiter` is a separate class for TPM tracking:

```python
# File: agora/coordinator/rate_limiter.py (add after existing RateLimiter)

class TokenRateLimiter:
    """Per-agent TPM token bucket tracking.

    Separate from RateLimiter (which handles speak/vote action limits).
    TokenRateLimiter tracks LLM API token usage.
    """

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def configure(self, agent_id: str, tpm_limit: int,
                  burst_factor: float = 1.5) -> None:
        """Create or reconfigure a bucket for an agent."""
        capacity = tpm_limit * burst_factor
        refill_rate = tpm_limit / 60.0
        with self._lock:
            existing = self._buckets.get(agent_id)
            if existing:
                # Preserve current token level, just change limits
                existing.capacity = capacity
                existing.refill_rate = refill_rate
            else:
                self._buckets[agent_id] = TokenBucket(
                    capacity=capacity, refill_rate=refill_rate
                )

    def remove(self, agent_id: str) -> None:
        """Remove bucket when agent deregisters."""
        with self._lock:
            self._buckets.pop(agent_id, None)

    def consume(self, agent_id: str, tokens: int) -> bool:
        """Try to consume tokens. Returns False if rate limited."""
        bucket = self._buckets.get(agent_id)
        if bucket is None:
            return True  # No limit configured → allow
        return bucket.consume(tokens)

    def get_status(self, agent_id: str) -> dict:
        """Get rate limit status for an agent."""
        bucket = self._buckets.get(agent_id)
        if bucket is None:
            return {
                "tpm_limit": 0,
                "tpm_burst_factor": 1.0,
                "tokens_available": 0,
                "tokens_used_this_window": 0,
                "usage_ratio": 0.0,
                "is_limited": False,
            }
        return {
            "tpm_limit": int(bucket.refill_rate * 60),
            "tpm_burst_factor": bucket.capacity / (bucket.refill_rate * 60)
                if bucket.refill_rate > 0 else 1.0,
            "tokens_available": int(bucket.available),
            "tokens_used_this_window": int(bucket.capacity - bucket.available),
            "usage_ratio": round(bucket.usage_ratio, 4),
            "is_limited": bucket.available <= 0,
        }

    def time_until_available(self, agent_id: str, needed: int) -> float:
        """Seconds until `needed` tokens become available."""
        bucket = self._buckets.get(agent_id)
        if bucket is None:
            return 0.0
        return bucket.time_until_available(needed)
```

### 2.2 Integration with Coordinator

The `TokenRateLimiter` instance lives on the coordinator app:

```python
# In coordinator/main.py or wherever the app state is initialized
app.state.token_limiter = TokenRateLimiter()
```

On agent registration (WELCOME message), configure the bucket:

```python
# In ws_handlers.py, after agent connects
config = agent.config  # AgentConfig from DB
app.state.token_limiter.configure(
    agent_id=agent.agent_id,
    tpm_limit=config.tpm_limit,
    burst_factor=getattr(config, 'tpm_burst_factor', 1.5),
)
```

On agent deregistration, remove the bucket:

```python
app.state.token_limiter.remove(agent_id)
```

### 2.3 Warning Thresholds

The coordinator monitors usage and sends WS warnings:

| Threshold | Message | When |
|-----------|---------|------|
| 80% used | `RATE_LIMIT_WARNING` | Agent has used 80% of burst capacity |
| 95% used | `RATE_LIMIT_WARNING` (urgent) | Agent is about to be limited |
| 100% used | `RATE_LIMITED` | Agent cannot consume more tokens |

Warnings are sent at most once per threshold crossing (not on every consume call).

```python
# Warning state tracking (per agent, in-memory)
_warning_state: dict[str, str] = {}  # agent_id → last threshold sent

THRESHOLDS = [
    (0.80, "warning"),
    (0.95, "critical"),
    (1.00, "limited"),
]

async def check_and_warn(agent_id: str, ws, bucket: TokenBucket):
    """Send WS warning if threshold crossed."""
    ratio = bucket.usage_ratio
    current_state = _warning_state.get(agent_id, "ok")

    for threshold, state in THRESHOLDS:
        if ratio >= threshold and current_state != state:
            _warning_state[agent_id] = state
            msg_type = "RATE_LIMITED" if state == "limited" else "RATE_LIMIT_WARNING"
            await ws.send_json({
                "type": msg_type,
                "payload": {
                    "usage_ratio": ratio,
                    "tokens_available": int(bucket.available),
                    "retry_after_seconds": bucket.time_until_available(1000),
                },
            })
            return

    # Reset warning state when usage drops below 80%
    if ratio < 0.80 and current_state != "ok":
        _warning_state[agent_id] = "ok"
```

## 3. Config

### 3.1 Per-Agent Config (AgentConfig model)

Already defined in DESIGN-phase9-agent-protocol.md §9.3a:

```python
class AgentConfig(BaseModel):
    max_concurrent_tasks: int = 2
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 120
    tpm_limit: int = 10000                   # Tokens per minute (0 = unlimited)
    tpm_burst_factor: float = 1.5            # Burst multiplier (1.0-3.0)
    allowed_discussion_roles: list[str] = Field(
        default_factory=lambda: ["participant"]
    )
    auto_accept_tasks: bool = False
```

New field: `tpm_burst_factor` (not in the original C.4 spec — added by this design).

### 3.2 Global Defaults

In coordinator config (`config.py` or `config.yaml`):

```python
# Environment variables / config.yaml
AGORA_DEFAULT_TPM_LIMIT = 10000       # Default for new agents
AGORA_DEFAULT_TPM_BURST = 1.5         # Default burst factor
AGORA_TPM_WARNING_THRESHOLD = 0.80    # When to send RATE_LIMIT_WARNING
```

### 3.3 Config Delivery

Agent receives its config in the WELCOME message (already designed in 9.3):

```json
{
  "type": "WELCOME",
  "payload": {
    "agent_id": "dev-alpha",
    "config": {
      "heartbeat_interval_seconds": 30,
      "tpm_limit": 10000,
      "tpm_burst_factor": 1.5,
      "max_concurrent_tasks": 2
    }
  }
}
```

## 4. API Endpoints

### 4.1 GET /api/v1/agents/{agent_id}/rate-limit

Get current rate limit status for an agent. Used by dashboards and the agent
itself to check remaining quota.

**Response 200:**
```json
{
  "agent_id": "dev-alpha",
  "tpm_limit": 10000,
  "tpm_burst_factor": 1.5,
  "tokens_available": 8500,
  "tokens_used_this_window": 6500,
  "usage_ratio": 0.4333,
  "is_limited": false,
  "retry_after_seconds": 0
}
```

**Response 404:** Agent not found or no rate limit configured.

### 4.2 POST /api/v1/agents/{agent_id}/rate-limit/report

Agent reports actual token usage after an LLM call. The coordinator deducts
from the bucket.

**Request:**
```json
{
  "tokens_used": 1500,
  "model": "claude-sonnet-4-20250514",
  "request_id": "req_abc123"
}
```

**Response 200:**
```json
{
  "agent_id": "dev-alpha",
  "accepted": true,
  "tokens_remaining": 7000,
  "usage_ratio": 0.5333
}
```

**Response 429 (if over limit):**
```json
{
  "agent_id": "dev-alpha",
  "accepted": false,
  "error": "rate_limited",
  "retry_after_seconds": 42.5
}
```

### 4.3 POST /api/v1/agents/{agent_id}/rate-limit/check

Pre-check: "can I make a call of N tokens?" Does NOT deduct tokens. The agent
uses this before the LLM call to avoid wasted API requests.

**Request:**
```json
{
  "estimated_tokens": 2000
}
```

**Response 200:**
```json
{
  "agent_id": "dev-alpha",
  "allowed": true,
  "tokens_available": 8500,
  "wait_seconds": 0
}
```

If not allowed:
```json
{
  "agent_id": "dev-alpha",
  "allowed": false,
  "tokens_available": 500,
  "wait_seconds": 9.0
}
```

### 4.4 PATCH /api/v1/agents/{agent_id}/config

Update agent config including TPM limits. Requires admin token.

**Request:**
```json
{
  "tpm_limit": 20000,
  "tpm_burst_factor": 2.0
}
```

**Response 200:** Updated AgentConfig.

**Response 401:** Missing or invalid admin token.

## 5. WebSocket Messages

### 5.1 RATE_LIMIT_WARNING

Server → Agent. Sent when agent crosses 80% or 95% usage threshold.

```json
{
  "type": "RATE_LIMIT_WARNING",
  "payload": {
    "level": "warning",
    "usage_ratio": 0.82,
    "tokens_available": 2700,
    "tpm_limit": 10000,
    "message": "Rate limit approaching: 82% of burst capacity used"
  }
}
```

`level` values: `"warning"` (80%), `"critical"` (95%).

### 5.2 RATE_LIMITED

Server → Agent. Sent when agent hits 100% usage. Agent should pause LLM calls.

```json
{
  "type": "RATE_LIMITED",
  "payload": {
    "usage_ratio": 1.0,
    "tokens_available": 0,
    "tpm_limit": 10000,
    "retry_after_seconds": 45.2,
    "message": "Rate limit exceeded. Retry in 45 seconds."
  }
}
```

### 5.3 RATE_LIMIT_RESET

Server → Agent. Sent when usage drops back below 80% after being limited.

```json
{
  "type": "RATE_LIMIT_RESET",
  "payload": {
    "usage_ratio": 0.75,
    "tokens_available": 3750
  }
}
```

### 5.4 MessageType Enum Update

Add to `MessageType` in `models.py`:

```python
RATE_LIMIT_WARNING = "RATE_LIMIT_WARNING"
RATE_LIMITED = "RATE_LIMITED"
RATE_LIMIT_RESET = "RATE_LIMIT_RESET"
```

## 6. Client Integration (AgoraClient.RateLimitTracker)

### 6.1 RateLimitTracker Class

The `AgoraClient` library includes a `RateLimitTracker` that agents use before
and after LLM calls:

```python
# File: agora/agent_client/rate_limit.py (NEW)

import asyncio
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitTracker:
    """Client-side rate limit tracker for LLM API calls.

    Maintains a local token bucket synced with coordinator config.
    Pre-checks before LLM calls, reports usage after.
    """

    tpm_limit: int = 10000
    burst_factor: float = 1.5
    _tokens: float = 0.0
    _last_refill: float = 0.0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self):
        self._tokens = self.tpm_limit * self.burst_factor
        self._last_refill = time.monotonic()

    def update_config(self, tpm_limit: int, burst_factor: float = 1.5) -> None:
        """Update limits from coordinator WELCOME/config-change."""
        self.tpm_limit = tpm_limit
        self.burst_factor = burst_factor
        # Don't reset tokens — preserve current level

    async def check(self, estimated_tokens: int) -> bool:
        """Pre-check: can we make this LLM call? Returns True if allowed."""
        async with self._lock:
            self._refill()
            if self._tokens >= estimated_tokens:
                return True
            return False

    async def wait_until_available(self, estimated_tokens: int,
                                   timeout: float = 120.0) -> bool:
        """Block until enough tokens are available, or timeout.

        Returns True if tokens became available, False on timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            async with self._lock:
                self._refill()
                if self._tokens >= estimated_tokens:
                    return True
            # Sleep for a short interval before retrying
            await asyncio.sleep(1.0)
        return False

    async def consume(self, tokens: int) -> None:
        """Deduct tokens after a successful LLM call."""
        async with self._lock:
            self._refill()
            self._tokens = max(0, self._tokens - tokens)

    async def report(self, tokens: int) -> None:
        """Alias for consume — report actual usage to local bucket."""
        await self.consume(tokens)

    def _refill(self) -> None:
        if self.tpm_limit <= 0:
            return  # Unlimited
        now = time.monotonic()
        elapsed = now - self._last_refill
        refill_rate = self.tpm_limit / 60.0
        capacity = self.tpm_limit * self.burst_factor
        self._tokens = min(capacity, self._tokens + elapsed * refill_rate)
        self._last_refill = now

    @property
    def available(self) -> float:
        """Current available tokens (non-blocking estimate)."""
        # Best-effort without lock — approximate is fine for status display
        if self.tpm_limit <= 0:
            return float("inf")
        now = time.monotonic()
        elapsed = now - self._last_refill
        refill_rate = self.tpm_limit / 60.0
        capacity = self.tpm_limit * self.burst_factor
        return min(capacity, self._tokens + elapsed * refill_rate)
```

### 6.2 Integration into AgoraClient

```python
# In agora/agent_client/client.py

class AgoraClient:
    def __init__(self, config: AgoraConfig) -> None:
        ...
        self.rate_limiter = RateLimitTracker()

    async def _on_welcome(self, payload: dict) -> None:
        """Handle WELCOME message, update rate limit config."""
        config = payload.get("config", {})
        if "tpm_limit" in config:
            self.rate_limiter.update_config(
                tpm_limit=config["tpm_limit"],
                burst_factor=config.get("tpm_burst_factor", 1.5),
            )

    async def report_token_usage(self, tokens_used: int,
                                 model: str = "",
                                 request_id: str = "") -> dict:
        """Report token usage to coordinator after LLM call.

        Also updates local bucket.
        """
        await self.rate_limiter.report(tokens_used)
        return await self._post(
            f"/api/v1/agents/{self._config.agent_id}/rate-limit/report",
            {"tokens_used": tokens_used, "model": model, "request_id": request_id},
        )

    async def check_rate_limit(self, estimated_tokens: int) -> dict:
        """Check if an LLM call of estimated_tokens is allowed."""
        return await self._post(
            f"/api/v1/agents/{self._config.agent_id}/rate-limit/check",
            {"estimated_tokens": estimated_tokens},
        )

    async def get_rate_limit_status(self) -> dict:
        """Get current rate limit status from coordinator."""
        return await self._get(
            f"/api/v1/agents/{self._config.agent_id}/rate-limit"
        )
```

### 6.3 Agent Usage Pattern

```python
# Typical agent code making an LLM call:

async def call_llm(prompt: str, max_tokens: int = 1000) -> str:
    estimated = len(prompt) // 4 + max_tokens  # Rough token estimate

    # 1. Pre-check local bucket
    if not await client.rate_limiter.check(estimated):
        # 2. Also check coordinator (belt + suspenders)
        status = await client.check_rate_limit(estimated)
        if not status.get("allowed"):
            wait = status.get("wait_seconds", 60)
            logger.warning(f"Rate limited, waiting {wait:.1f}s")
            await asyncio.sleep(wait)

    # 3. Make the actual LLM call
    response = await llm_api.complete(prompt, max_tokens=max_tokens)
    actual_tokens = response.usage.total_tokens

    # 4. Report usage to local bucket + coordinator
    await client.rate_limiter.report(actual_tokens)
    await client.report_token_usage(actual_tokens)

    return response.text
```

## 7. Storage

### 7.1 In-Memory (Primary)

The `TokenRateLimiter` keeps all bucket state in memory. This is the primary
enforcement path — fast, no DB overhead.

### 7.2 Periodic DB Flush (Secondary)

For persistence across coordinator restarts, a background task flushes usage
snapshots to the database every 60 seconds:

```sql
-- New table: rate_limit_usage
CREATE TABLE IF NOT EXISTS rate_limit_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    window_start REAL NOT NULL,       -- Unix timestamp of window start
    tokens_consumed INTEGER NOT NULL DEFAULT 0,
    tpm_limit INTEGER NOT NULL,
    last_updated REAL NOT NULL,
    UNIQUE(agent_id, window_start)
);
```

```python
async def flush_rate_limits():
    """Background task: flush in-memory buckets to DB every 60s."""
    while True:
        await asyncio.sleep(60)
        now = time.time()
        window_start = now - (now % 60)  # Align to minute boundary
        for agent_id, bucket in app.state.token_limiter._buckets.items():
            status = app.state.token_limiter.get_status(agent_id)
            await db.execute(
                """INSERT OR REPLACE INTO rate_limit_usage
                   (agent_id, window_start, tokens_consumed, tpm_limit, last_updated)
                   VALUES (?, ?, ?, ?, ?)""",
                (agent_id, window_start,
                 status["tokens_used_this_window"],
                 status["tpm_limit"], now),
            )
```

On coordinator restart, restore buckets from the most recent window:

```python
async def restore_rate_limits():
    """Restore rate limit state from DB on startup."""
    now = time.time()
    window_start = now - (now % 60)
    rows = await db.fetch_all(
        "SELECT agent_id, tokens_consumed, tpm_limit FROM rate_limit_usage "
        "WHERE window_start = ?",
        (window_start,)
    )
    for row in rows:
        app.state.token_limiter.configure(row["agent_id"], row["tpm_limit"])
        # Pre-consume tokens that were already used this window
        if row["tokens_consumed"] > 0:
            app.state.token_limiter.consume(row["agent_id"], row["tokens_consumed"])
```

### 7.3 Cleanup

Old rate limit records are cleaned up periodically:

```python
# Keep last 24 hours of data
DELETE FROM rate_limit_usage WHERE window_start < ?;
```

## 8. Edge Cases

### 8.1 Agent with tpm_limit = 0 (Unlimited)

`tpm_limit = 0` means "no rate limit." The `TokenRateLimiter` skips bucket
creation for this agent, and `consume()` always returns True.

### 8.2 Agent Reconfiguration Mid-Window

When an admin changes `tpm_limit` via `PATCH /config`:
1. Coordinator updates the bucket's `capacity` and `refill_rate`
2. Current token level is preserved (not reset)
3. A `CONFIG_UPDATED` WS message is sent to the agent
4. Agent's local `RateLimitTracker` updates its config

### 8.3 Coordinator Restart

On restart:
1. Buckets are restored from the most recent `rate_limit_usage` window
2. Agents reconnect via WebSocket, receive fresh WELCOME with config
3. Agents reset their local buckets to full capacity (safe — coordinator
   tracks actual usage)

### 8.4 Agent Disconnect During Rate Limit

If an agent disconnects while rate-limited:
1. Bucket continues refilling on the coordinator
2. When agent reconnects, it gets current bucket state via WELCOME
3. No special handling needed — token bucket is self-correcting

### 8.5 Multiple Agents Sharing One API Key

Agora doesn't manage API keys — agents bring their own. If two agents share
one API key (e.g., both use the same Anthropic key), the LLM provider's own
rate limits apply. Agora's TPM limits are per-agent, not per-API-key. This is
a known limitation documented for operators.

### 8.6 Client-Side Only (Coordinator Unreachable)

If the coordinator is unreachable:
1. Agent's local `RateLimitTracker` still enforces limits
2. Agent can't report usage → local bucket may drift from coordinator
3. On reconnect, agent gets fresh config + bucket state from WELCOME
4. Agent resets local bucket to coordinator's state

### 8.7 Token Estimation Accuracy

Agents estimate tokens before LLM calls (prompt_length/4 + max_tokens).
This is approximate. The coordinator's `report` endpoint accepts actual
token counts from the LLM response. The local bucket may be slightly off,
but the coordinator's bucket is authoritative.

## 9. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `agora/coordinator/rate_limiter.py` | Modify | Add `TokenBucket`, `TokenRateLimiter` classes |
| `agora/coordinator/models.py` | Modify | Add `RATE_LIMIT_WARNING`, `RATE_LIMITED`, `RATE_LIMIT_RESET` to `MessageType` |
| `agora/coordinator/models.py` | Modify | Add `tpm_burst_factor` to `AgentConfig` (if not yet implemented from 9.3a) |
| `agora/coordinator/schema.py` | Modify | Add `rate_limit_usage` table, bump `SCHEMA_VERSION` |
| `agora/coordinator/ws_handlers.py` | Modify | Add rate limit warning logic, configure bucket on connect |
| `agora/coordinator/routes.py` | Modify | Add `/agents/{id}/rate-limit*` endpoints |
| `agora/agent_client/rate_limit.py` | **NEW** | `RateLimitTracker` class |
| `agora/agent_client/client.py` | Modify | Integrate `RateLimitTracker`, add `report_token_usage()`, `check_rate_limit()` |
| `agora/agent_client/__init__.py` | Modify | Export `RateLimitTracker` |
| `tests/test_rate_limiter.py` | Modify | Add `TokenBucket`, `TokenRateLimiter` tests |
| `tests/test_rate_limit_tracker.py` | **NEW** | `RateLimitTracker` tests |

## 10. Files NOT Changed

- `agora/coordinator/voting/*` — no changes
- `agora/coordinator/discussion/*` — no changes
- `agora/coordinator/task_*.py` — no changes (tasks don't directly interact with rate limiter)
- `agora/coordinator/observability/*` — no changes (metrics can be added later)

## 11. Testing Strategy

### Unit Tests

1. **TokenBucket**: refill math, burst behavior, concurrent consume, edge cases
   (capacity=0, negative tokens)
2. **TokenRateLimiter**: configure/remove agents, consume tracking, status
   reporting, unlimited agent (tpm_limit=0)
3. **RateLimitTracker**: local bucket sync, config update, wait_until_available
4. **API endpoints**: 200, 404, 429 responses

### Integration Tests

1. Agent connects → WELCOME includes tpm config → local tracker synced
2. Agent reports usage → coordinator bucket updated → GET /rate-limit reflects it
3. Agent exceeds limit → RATE_LIMITED WS message received
4. Coordinator restart → bucket restored from DB

## 12. Migration from Existing RateLimiter

The existing `RateLimiter` (sliding window for speak/vote actions) is NOT
replaced. It handles a different concern (discussion participation rate
limiting). The new `TokenRateLimiter` is additive — it handles LLM API
token usage tracking.

Both coexist in `agora/coordinator/rate_limiter.py`:
- `RateLimiter` — speak/vote action limits (existing, unchanged)
- `TokenBucket` — token bucket data structure (new)
- `TokenRateLimiter` — per-agent TPM tracking (new)
