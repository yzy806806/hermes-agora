"""Rate limiting for Hermes Agora using sliding window counters."""
import time
from collections import defaultdict

from .input_validation import ValidationConfig


class RateLimiter:
    """Per-agent rate limiting with 1-minute sliding window."""

    def __init__(self, config: ValidationConfig | None = None):
        self.config = config or ValidationConfig()
        self._counts: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._limits: dict[str, int] = {
            "speak": self.config.rate_limit_speak,
            "vote": self.config.rate_limit_vote,
        }

    def _window(self) -> float:
        return time.time() - 60.0

    def check_rate(self, agent_id: str, action: str) -> bool:
        """Return True if action allowed, False if rate exceeded."""
        limit = self._limits.get(action)
        if limit is None:
            return True
        cutoff = self._window()
        timestamps = [t for t in self._counts[agent_id][action] if t > cutoff]
        self._counts[agent_id][action] = timestamps
        if len(timestamps) >= limit:
            return False
        timestamps.append(time.time())
        return True

    def get_remaining(self, agent_id: str, action: str) -> int:
        """Return remaining quota for action in current window."""
        limit = self._limits.get(action, 0)
        cutoff = self._window()
        timestamps = [t for t in self._counts[agent_id][action] if t > cutoff]
        self._counts[agent_id][action] = timestamps
        return max(0, limit - len(timestamps))

    def reset(self, agent_id: str) -> None:
        """Reset all rate limit counters for an agent."""
        self._counts.pop(agent_id, None)


# ---------------------------------------------------------------------------
# Phase 9.4: Token Bucket rate limiting (TPM tracking)
# ---------------------------------------------------------------------------


import threading
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Thread-safe token bucket for TPM rate limiting."""

    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.monotonic()

    def consume(self, count: int) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        with self._lock:
            self._refill()
            if self.tokens >= count:
                self.tokens -= count
                return True
            return False

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    @property
    def available(self) -> float:
        """Current available tokens (triggers refill)."""
        with self._lock:
            self._refill()
            return self.tokens

    @property
    def usage_ratio(self) -> float:
        """0.0 (full) to 1.0 (empty)."""
        if self.capacity <= 0:
            return 0.0
        return 1.0 - (self.available / self.capacity)

    def time_until_available(self, needed: int) -> float:
        """Seconds until `needed` tokens become available."""
        avail = self.available
        if avail >= needed:
            return 0.0
        if self.refill_rate <= 0:
            return float("inf")
        return (needed - avail) / self.refill_rate
