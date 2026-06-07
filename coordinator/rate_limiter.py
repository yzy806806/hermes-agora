"""Rate limiting for Hermes Agora using sliding window counters."""
import time
from collections import defaultdict

from coordinator.input_validation import ValidationConfig


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
