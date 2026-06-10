"""Tests for RetryPolicy model (Phase 10.1e)."""

import pytest
from agora.coordinator.task_retry_policy import (
    BackoffStrategy, RetryPolicy, FailureDecision,
)


class TestRetryPolicy:
    def test_default_no_retry(self):
        p = RetryPolicy()
        assert not p.can_retry(0)

    def test_max_retries_3(self):
        p = RetryPolicy(max_retries=3)
        assert p.can_retry(0)
        assert p.can_retry(2)
        assert not p.can_retry(3)

    def test_infinite_retry(self):
        p = RetryPolicy(max_retries=-1)
        assert p.can_retry(0)
        assert p.can_retry(1000)

    def test_fixed_backoff(self):
        p = RetryPolicy(backoff_strategy=BackoffStrategy.FIXED, initial_delay=2.0)
        assert p.get_delay(0) == 2.0
        assert p.get_delay(5) == 2.0

    def test_exponential_backoff(self):
        p = RetryPolicy(
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            initial_delay=1.0,
        )
        assert p.get_delay(0) == 1.0
        assert p.get_delay(1) == 2.0
        assert p.get_delay(2) == 4.0

    def test_exponential_capped_at_60(self):
        p = RetryPolicy(initial_delay=1.0)
        assert p.get_delay(10) == 60.0


class TestFailureDecision:
    def test_values(self):
        assert FailureDecision.RETRY.value == "retry"
        assert FailureDecision.ABORT_TASK.value == "abort_task"
        assert FailureDecision.ABORT_GRAPH.value == "abort_graph"
