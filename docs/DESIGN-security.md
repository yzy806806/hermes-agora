# Phase 5 Design: Security

> This document outlines the security strategy for Hermes Agora Phase 5.

## Overview

The multi-agent discussion framework needs protection against:
- Agent deadlock in discussions
- Collusion between agents
- Input validation and injection protection
- Access control

---

## 1. Prevent Agent Deadlock

### 1.1 Circular Dependency Prevention

**Scenario:** Two or more agents continuously reference each other, blocking discussion.

**Design:**
- Track agent message references in storage
- If Agent A references Agent B and Agent B references Agent A within N messages:
  1. Flag as potential deadlock
  2. Inject BREAK message to redirect discussion
  3. Log for operator review

**Implementation:**
```python
# In storage/messages.py
async def check_circular_references(motion_id: str) -> list[str]:
    """Find circular reference chains."""
    messages = await self.get_messages(motion_id)
    references = {}  # agent_id → set of referenced agent_ids
    
    for msg in messages:
        refs = extract_references(msg.content)  # Extract @mentions
        references.setdefault(msg.agent_id, set()).update(refs)
    
    # Find cycles
    cycles = []
    for agent in references:
        if agent in references[agent]:
            cycles.append(agent)  # Self-reference
    
    return cycles
```

### 1.2 Discussion Progress Enforcement

**Design:**
- Maximum consecutive messages per agent: 3 (configurable)
- After 3, must wait for other agents to speak
- Prevents single agent from dominating

---

## 2. Prevent Collusion

### 2.1 Voting Privacy

**Current State:** Votes are broadcast after all votes collected.

**Design:**
- Implement commit-reveal scheme for votes:
  1. Agent sends encrypted vote (commitment)
  2. After all commits received, request reveal
  3. Agent decrypts and sends actual vote
- This prevents other agents from observing vote patterns midstream

**Implementation:**
```python
class VotingPhase:
    def __init__(self):
        self.commitments: dict[str, str] = {}  # agent_id → hash
        self.revealed: dict[str, str] = {}     # agent_id → actual vote
    
    async def receive_commit(self, agent_id: str, commit: str):
        self.commitments[agent_id] = commit
    
    async def receive_reveal(self, agent_id: str, vote: str, key: str):
        # Verify commit matches reveal
        expected_hash = hashlib.sha256(f"{vote}:{key}".encode()).hexdigest()
        if expected_hash != self.commitments.get(agent_id):
            raise ValueError("Commit mismatch")
        self.revealed[agent_id] = vote
```

### 2.2 Agent Identity Verification

**Design:**
- Each agent registration includes signed token from Hermes
- Server validates agent identity before allowing WS connection
- Prevents impersonation attacks

---

## 3. Input Validation and Injection Protection

### 3.1 Message Sanitization

**Design:**
- Strip or escape HTML/JS in agent messages
- Block mentions of internal endpoints/URLs
- Limit message length (max 10000 characters)

**Implementation:**
```python
import html
import re

def sanitize_message(content: str) -> str:
    # Escape HTML
    content = html.escape(content)
    
    # Remove/replace dangerous patterns
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.I)
    content = re.sub(r'javascript:', '', content, flags=re.I)
    content = re.sub(r'on\w+\s*=', '', content, flags=re.I)
    
    # Limit length
    return content[:10000]

# In ws_endpoint.py handle_speak
async def handle_speak(agent_id, payload, storage, sm, manager):
    content = payload.get("content", "")
    sanitized = sanitize_message(content)
    # Proceed with sanitized content
```

### 3.2 SQL Injection Prevention

**Current State:** Uses parameterized queries. Verify.

**Design:**
- All database queries use parameterized statements
- No string concatenation for SQL
- Regular security audit with automated scanning

**Verification:**
```bash
# Run bandit for SQL injection patterns
bandit -r coordinator/
```

### 3.3 Rate Limiting

**Design:**
- Per-agent rate limits:
  - Messages: max 10 per minute
  - Votes: max 1 per motion
  - Registration: max 5 per minute
- Implement using in-memory token bucket

**Implementation:**
```python
class RateLimiter:
    def __init__(self):
        self.buckets: dict[str, TokenBucket] = {}
    
    def check(self, key: str, limit: int, window: int) -> bool:
        bucket = self.buckets.setdefault(key, TokenBucket(limit, window))
        return bucket.consume()

class TokenBucket:
    def __init__(self, rate: int, window: int):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
    
    def consume(self) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.rate, self.tokens + elapsed * self.rate / window)
        self.last_update = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

# Usage in router.py
rate_limiter = RateLimiter()

@router.post("/motions")
async def create_motion(request: MotionCreateRequest):
    if not rate_limiter.check(f"motion:{request.agent_id}", 10, 60):
        raise HTTPException(status_code=429, detail="Rate limited")
```

---

## 4. Access Control

### 4.1 Permission Levels

**Design:**
- `ADMIN`: Full access, can delete any motion/agent
- `AGENT`: Participate in discussions, vote
- `READONLY`: Can view motions and results, no write

**Implementation:**
```python
from enum import Enum

class PermissionLevel(Enum):
    ADMIN = "admin"
    AGENT = "agent"
    READONLY = "readonly"

def require_permission(level: PermissionLevel):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request, *args, **kwargs):
            if request.permission < level:
                raise HTTPException(403, "Forbidden")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@router.delete("/motions/{motion_id}")
@require_permission(PermissionLevel.ADMIN)
async def delete_motion(motion_id: str):
    ...
```

### 4.2 Motion Access Control

**Design:**
- Public motions: any registered agent can join
- Private motions: only invited agents can participate
- Invitation system with tokens

---

## 5. Network Security

### 5.1 WebSocket Origins

**Design:**
- Validate Origin header in WebSocket handshake
- Whitelist allowed origins in config
- Reject connections from unauthorized origins

**Implementation in main.py:**
```python
app.add_websocket_route(
    "/ws/{agent_id}",
    websocket_endpoint,
    name="ws",
)

# Or via middleware
@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    origin = websocket.headers.get("origin")
    allowed_origins = config.get("allowed_origins", [])
    if allowed_origins and origin not in allowed_origins:
        await websocket.close(code=4003, reason="Origin not allowed")
        return
```

### 5.2 TLS Configuration

**Design:**
- Require WSS (WebSocket Secure) in production
- HTTP -> WSS redirect
- Certificate configuration via environment

---

## Implementation Phases

| Phase | Feature | Priority |
|-------|---------|----------|
| 5.1 | Input sanitization | P0 |
| 5.2 | Rate limiting | P0 |
| 5.3 | Permission levels | P1 |
| 5.4 | Circular dependency prevention | P1 |
| 5.5 | Collusion prevention (commit-reveal) | P2 |
| 5.6 | Agent identity verification | P2 |
| 5.7 | Motion access control | P2 |
| 5.8 | Network security (origins, TLS) | P2 |

---

## Files to Create/Modify

New files:
- `coordinator/security/rate_limiter.py` - Rate limiting
- `coordinator/security/sanitizer.py` - Input sanitization
- `coordinator/security/permissions.py` - Access control

Modified files:
- `coordinator/ws_endpoint.py` - Sanitization, origin validation
- `coordinator/router.py` - Rate limiting, permission checks
- `coordinator/storage/messages.py` - Circular detection
- `coordinator/voting/*.py` - Commit-reveal scheme
- `coordinator/main.py` - TLS config

---

## Testing Strategy

1. Unit test sanitizer with XSS payloads
2. Integration test rate limiting behavior
3. Unit test permission check logic
4. Integration test commit-reveal voting
5. Security audit with OWASP ZAP or similar

---

## Configuration

Add to `config.yaml`:

```yaml
security:
  rate_limits:
    messages_per_minute: 10
    votes_per_motion: 1
    registrations_per_minute: 5
  allowed_origins:
    - "https://hermes.example.com"
  tls_enabled: true
  voting:
    use_commit_reveal: true
  collusion:
    max_consecutive_per_agent: 3
  deadlocks:
    circular_detection: true
    max_references_per_message: 5
```