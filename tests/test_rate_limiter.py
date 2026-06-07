"""Tests for RateLimiter."""
import pytest
from coordinator.input_validation import ValidationConfig
from coordinator.rate_limiter import RateLimiter


class TestRateLimiter:
    def setup_method(self):
        self.cfg = ValidationConfig(rate_limit_speak=3, rate_limit_vote=2)
        self.limiter = RateLimiter(self.cfg)

    def test_allows_under_limit(self):
        for _ in range(3):
            assert self.limiter.check_rate("a1", "speak") is True

    def test_blocks_over_limit(self):
        for _ in range(3):
            self.limiter.check_rate("a1", "speak")
        assert self.limiter.check_rate("a1", "speak") is False

    def test_agents_independent(self):
        for _ in range(3):
            self.limiter.check_rate("a1", "speak")
        assert self.limiter.check_rate("a2", "speak") is True

    def test_get_remaining(self):
        self.limiter.check_rate("a1", "speak")
        assert self.limiter.get_remaining("a1", "speak") == 2

    def test_reset(self):
        for _ in range(3):
            self.limiter.check_rate("a1", "speak")
        self.limiter.reset("a1")
        assert self.limiter.check_rate("a1", "speak") is True

    def test_unknown_action_allowed(self):
        assert self.limiter.check_rate("a1", "unknown") is True
