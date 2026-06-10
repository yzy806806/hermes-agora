"""Tests for RateLimitTracker — client-side token bucket."""
from __future__ import annotations

import asyncio
import time

import pytest

from agora.agent_client.rate_limit import RateLimitTracker


class TestRateLimitTrackerInit:
    """Initialization and config tests."""

    def test_default_init(self):
        tracker = RateLimitTracker()
        assert tracker.tpm_limit == 10000
        assert tracker.burst_factor == 1.5
        assert tracker.capacity == 15000.0
        assert tracker.refill_rate == pytest.approx(166.67, rel=0.01)

    def test_custom_init(self):
        tracker = RateLimitTracker(tpm_limit=5000, burst_factor=2.0)
        assert tracker.capacity == 10000.0
        assert tracker.refill_rate == pytest.approx(83.33, rel=0.01)

    def test_tokens_start_at_capacity(self):
        tracker = RateLimitTracker(tpm_limit=1000, burst_factor=1.5)
        assert tracker._tokens == 1500.0


class TestRateLimitTrackerCheck:
    """Pre-check (local bucket) tests."""

    @pytest.mark.asyncio
    async def test_check_allowed(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        assert await tracker.check(500) is True

    @pytest.mark.asyncio
    async def test_check_denied(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        # Consume most tokens first
        await tracker.consume(1400)
        assert await tracker.check(200) is False

    @pytest.mark.asyncio
    async def test_check_unlimited(self):
        tracker = RateLimitTracker(tpm_limit=0)
        assert await tracker.check(999999) is True


class TestRateLimitTrackerConsume:
    """Token consumption and refill tests."""

    @pytest.mark.asyncio
    async def test_consume_reduces_tokens(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        await tracker.consume(500)
        assert tracker._tokens == pytest.approx(1000.0, abs=1.0)

    @pytest.mark.asyncio
    async def test_consume_clamps_to_zero(self):
        tracker = RateLimitTracker(tpm_limit=100)
        await tracker.consume(9999)
        assert tracker._tokens == 0.0

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        tracker = RateLimitTracker(tpm_limit=600)  # 10 tokens/sec
        await tracker.consume(900)  # leaves 0
        await asyncio.sleep(0.5)  # ~5 tokens refilled
        avail = tracker.available
        assert 3.0 < avail < 8.0  # rough range

    @pytest.mark.asyncio
    async def test_consume_unlimited_noop(self):
        tracker = RateLimitTracker(tpm_limit=0)
        await tracker.consume(9999)
        assert tracker.available == float("inf")


class TestRateLimitTrackerConfig:
    """Config update tests."""

    def test_update_config_preserves_tokens(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        tracker._tokens = 500.0
        tracker.update_config(tpm_limit=2000, burst_factor=2.0)
        assert tracker.tpm_limit == 2000
        assert tracker.burst_factor == 2.0
        assert tracker._tokens == 500.0  # preserved

    def test_update_config_changes_capacity(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        tracker.update_config(tpm_limit=2000, burst_factor=2.0)
        assert tracker.capacity == 4000.0
        assert tracker.refill_rate == pytest.approx(33.33, rel=0.01)


class TestRateLimitTrackerWait:
    """wait_until_available tests."""

    @pytest.mark.asyncio
    async def test_wait_succeeds_immediately(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        assert await tracker.wait_until_available(500, timeout=1.0) is True

    @pytest.mark.asyncio
    async def test_wait_times_out(self):
        tracker = RateLimitTracker(tpm_limit=1000)
        await tracker.consume(1400)
        result = await tracker.wait_until_available(200, timeout=0.3)
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_unlimited(self):
        tracker = RateLimitTracker(tpm_limit=0)
        assert await tracker.wait_until_available(999999) is True
