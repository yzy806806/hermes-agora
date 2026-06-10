"""Client-side rate limit tracker for LLM API calls.

Maintains a local token bucket synced with coordinator config.
Pre-checks before LLM calls, reports usage after.
"""
from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RateLimitTracker:
    """Client-side token bucket for TPM rate limiting.

    Syncs tpm_limit + burst_factor from WELCOME AgentConfig.
    Pre-checks before LLM call, reports usage after call.
    Graceful degradation: local-only bucket if coordinator unreachable.
    """

    tpm_limit: int = 10000
    burst_factor: float = 1.5
    _tokens: float = field(default=0.0, repr=False)
    _last_refill: float = field(default=0.0, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        self._tokens = self.tpm_limit * self.burst_factor
        self._last_refill = time.monotonic()

    @property
    def capacity(self) -> float:
        """Max token capacity (tpm_limit * burst_factor)."""
        return self.tpm_limit * self.burst_factor

    @property
    def refill_rate(self) -> float:
        """Tokens per second (tpm_limit / 60)."""
        return self.tpm_limit / 60.0 if self.tpm_limit > 0 else 0.0

    def update_config(self, tpm_limit: int, burst_factor: float = 1.5) -> None:
        """Update limits from coordinator WELCOME or config-change."""
        self.tpm_limit = tpm_limit
        self.burst_factor = burst_factor
        # Don't reset tokens — preserve current level

    async def check(self, estimated_tokens: int) -> bool:
        """Pre-check: can we make this LLM call? Returns True if allowed."""
        if self.tpm_limit <= 0:
            return True  # Unlimited
        async with self._lock:
            self._refill()
            return self._tokens >= estimated_tokens

    async def wait_until_available(
        self, estimated_tokens: int, timeout: float = 120.0,
    ) -> bool:
        """Block until enough tokens available, or timeout.

        Uses exponential backoff: starts at 0.5s, doubles up to 5s.
        Returns True if tokens became available, False on timeout.
        """
        if self.tpm_limit <= 0:
            return True
        deadline = time.monotonic() + timeout
        delay = 0.5
        while time.monotonic() < deadline:
            async with self._lock:
                self._refill()
                if self._tokens >= estimated_tokens:
                    return True
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5.0)
        return False

    async def consume(self, tokens: int) -> None:
        """Deduct tokens after a successful LLM call."""
        if self.tpm_limit <= 0:
            return
        async with self._lock:
            self._refill()
            self._tokens = max(0, self._tokens - tokens)

    async def report(self, tokens: int) -> None:
        """Report actual usage to local bucket (alias for consume)."""
        await self.consume(tokens)

    def _refill(self) -> None:
        """Add tokens based on elapsed time. Must be called under lock."""
        if self.tpm_limit <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.capacity, self._tokens + elapsed * self.refill_rate,
        )
        self._last_refill = now

    @property
    def available(self) -> float:
        """Current available tokens (non-blocking estimate)."""
        if self.tpm_limit <= 0:
            return float("inf")
        now = time.monotonic()
        elapsed = now - self._last_refill
        return min(self.capacity, self._tokens + elapsed * self.refill_rate)
