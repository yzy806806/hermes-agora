"""Phase 9.4: Per-agent TPM token bucket tracking.

Separate from RateLimiter (which handles speak/vote action limits).
TokenRateLimiter tracks LLM API token usage via TokenBucket.
"""

import threading

from .rate_limiter import TokenBucket


class TokenRateLimiter:
    """Per-agent TPM token bucket tracking."""

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def configure(
        self, agent_id: str, tpm_limit: int, burst_factor: float = 1.5,
    ) -> None:
        """Create or reconfigure a bucket for an agent."""
        if tpm_limit <= 0:
            # tpm_limit=0 means unlimited — no bucket needed
            self.remove(agent_id)
            return
        capacity = tpm_limit * burst_factor
        refill_rate = tpm_limit / 60.0
        with self._lock:
            existing = self._buckets.get(agent_id)
            if existing:
                existing.capacity = capacity
                existing.refill_rate = refill_rate
            else:
                self._buckets[agent_id] = TokenBucket(
                    capacity=capacity, refill_rate=refill_rate,
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
                "tpm_limit": 0, "tpm_burst_factor": 1.0,
                "tokens_available": 0, "tokens_used_this_window": 0,
                "usage_ratio": 0.0, "is_limited": False,
            }
        tpm = int(bucket.refill_rate * 60)
        return {
            "tpm_limit": tpm,
            "tpm_burst_factor": round(bucket.capacity / tpm, 2) if tpm > 0 else 1.0,
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
