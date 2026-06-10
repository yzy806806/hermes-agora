"""Retry policy models for task failure handling (Phase 10.1e).

Implements Section A.8 retry configuration:
- BackoffStrategy: fixed or exponential
- RetryPolicy: max_retries, backoff, initial_delay
- FailureDecision: outcome enum for handle_task_failure
"""

from __future__ import annotations

import math
from enum import Enum

from pydantic import BaseModel


class BackoffStrategy(str, Enum):
    """Backoff strategy for retries."""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"


class RetryPolicy(BaseModel):
    """Configuration for task retry behavior."""
    max_retries: int = 0  # 0=no retry, -1=infinite
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    initial_delay: float = 1.0  # seconds

    def get_delay(self, attempt: int) -> float:
        """Calculate delay before the next retry attempt."""
        if self.backoff_strategy == BackoffStrategy.FIXED:
            return self.initial_delay
        # Exponential with cap at 60s
        return min(self.initial_delay * math.pow(2, attempt), 60.0)

    def can_retry(self, current_retries: int) -> bool:
        """Check if another retry is allowed."""
        if self.max_retries < 0:
            return True  # infinite retries
        return current_retries < self.max_retries


class FailureDecision(str, Enum):
    """Outcome of failure handling."""
    RETRY = "retry"
    ABORT_TASK = "abort_task"
    ABORT_GRAPH = "abort_graph"
