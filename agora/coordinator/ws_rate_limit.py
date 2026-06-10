"""Phase 9.4: Rate limit warning threshold tracking and WS notification."""

from __future__ import annotations

from .models import MessageType
from .token_rate_limiter import TokenRateLimiter
from .rate_limiter import TokenBucket

# Warning thresholds: (usage_ratio, state_name, message_type)
THRESHOLDS = [
    (0.80, "warning", MessageType.RATE_LIMIT_WARNING),
    (0.95, "critical", MessageType.RATE_LIMIT_WARNING),
    (1.00, "limited", MessageType.RATE_LIMITED),
]

# Per-agent warning state: agent_id → last threshold state sent
_warning_state: dict[str, str] = {}


async def check_and_warn(
    agent_id: str, hub, token_limiter: TokenRateLimiter,
) -> None:
    """Send WS warning if threshold crossed. Call after token report."""
    bucket = token_limiter._buckets.get(agent_id)
    if bucket is None:
        return
    ratio = bucket.usage_ratio
    current = _warning_state.get(agent_id, "ok")

    for threshold, state, msg_type in THRESHOLDS:
        if ratio >= threshold and current != state:
            _warning_state[agent_id] = state
            level = "critical" if state == "critical" else state
            payload = {
                "level": level,
                "usage_ratio": round(ratio, 4),
                "tokens_available": int(bucket.available),
                "tpm_limit": int(bucket.refill_rate * 60),
            }
            if state == "limited":
                payload["retry_after_seconds"] = bucket.time_until_available(1000)
                payload["message"] = "Rate limit exceeded."
            else:
                pct = int(ratio * 100)
                payload["message"] = f"Rate limit approaching: {pct}% used"
            await hub.send(agent_id, {"type": msg_type, "payload": payload})
            return

    # Reset when usage drops below 80%
    if ratio < 0.80 and current != "ok":
        _warning_state[agent_id] = "ok"
        await hub.send(agent_id, {
            "type": MessageType.RATE_LIMIT_RESET,
            "payload": {
                "usage_ratio": round(ratio, 4),
                "tokens_available": int(bucket.available),
            },
        })


def reset_warning_state(agent_id: str) -> None:
    """Clear warning state when agent disconnects."""
    _warning_state.pop(agent_id, None)
