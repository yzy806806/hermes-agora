"""Failure handling logic for parallel task execution (Phase 10.1e).

Implements Section A.8 failure handling:
- handle_task_failure: decide retry / abort / continue
- Delegates cascading and graph-abort to task_retry_helpers
"""

from __future__ import annotations

import logging
from typing import Any

from .task_retry_policy import FailureDecision, RetryPolicy
from .task_retry_helpers import abort_graph, cascade_block_dependents

logger = logging.getLogger(__name__)


async def handle_task_failure(
    task_id: str,
    error: str,
    policy: RetryPolicy,
    storage: Any,
    hub: Any,
    abort_on_failure: bool = False,
    retry_count: int = 0,
) -> FailureDecision:
    """Decide what to do when a task fails.

    Returns the decision taken. Side effects:
    - RETRY: update task status to pending, send TASK_RETRY
    - ABORT_TASK: cascade-block all dependent tasks
    - ABORT_GRAPH: cancel all running tasks in the graph
    """
    if policy.can_retry(retry_count):
        delay = policy.get_delay(retry_count)
        logger.info(
            "Retrying task %s (attempt %d) after %.1fs: %s",
            task_id, retry_count + 1, delay, error,
        )
        await storage.update_task_status(
            task_id, "pending", error_message=error,
        )
        await hub.broadcast({
            "type": "TASK_RETRY",
            "task_id": task_id,
            "reason": error,
            "attempt": retry_count + 1,
            "delay_seconds": delay,
        })
        return FailureDecision.RETRY

    if abort_on_failure:
        logger.warning("Abort-on-failure: cancelling graph for task %s", task_id)
        await abort_graph(task_id, storage, hub)
        return FailureDecision.ABORT_GRAPH

    # Default: abort just this task, cascade-block dependents
    await cascade_block_dependents(task_id, storage, hub)
    return FailureDecision.ABORT_TASK
