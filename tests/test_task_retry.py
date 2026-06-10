"""Tests for handle_task_failure and cascade/abort helpers (Phase 10.1e)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.task_retry_policy import RetryPolicy, FailureDecision
from agora.coordinator.task_retry import handle_task_failure
from agora.coordinator.task_retry_helpers import (
    cascade_block_dependents, abort_graph,
)


def _make_storage(tasks=None, graph_id="g1"):
    storage = AsyncMock()
    storage.get_task = AsyncMock(return_value={"id": "t1", "graph_id": graph_id})
    storage.get_tasks_by_graph = AsyncMock(return_value=tasks or [])
    return storage


def _make_hub():
    hub = AsyncMock()
    hub.broadcast = AsyncMock()
    return hub


@pytest.mark.asyncio
async def test_retry_decision():
    policy = RetryPolicy(max_retries=2)
    storage = _make_storage()
    hub = _make_hub()
    result = await handle_task_failure(
        "t1", "timeout", policy, storage, hub, retry_count=0,
    )
    assert result == FailureDecision.RETRY
    storage.update_task_status.assert_called_with(
        "t1", "pending", error_message="timeout",
    )
    hub.broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_abort_task_cascades():
    policy = RetryPolicy(max_retries=0)
    tasks = [
        {"id": "t1", "status": "failed", "depends_on": []},
        {"id": "t2", "status": "pending", "depends_on": ["t1"]},
    ]
    storage = _make_storage(tasks=tasks)
    hub = _make_hub()
    result = await handle_task_failure("t1", "error", policy, storage, hub)
    assert result == FailureDecision.ABORT_TASK
    storage.update_task_status.assert_called_with(
        "t2", "failed", error_message="Blocked by failed task t1",
    )


@pytest.mark.asyncio
async def test_abort_graph_mode():
    policy = RetryPolicy(max_retries=0)
    tasks = [
        {"id": "t1", "status": "failed", "depends_on": []},
        {"id": "t2", "status": "running", "depends_on": []},
        {"id": "t3", "status": "pending", "depends_on": []},
    ]
    storage = _make_storage(tasks=tasks)
    hub = _make_hub()
    result = await handle_task_failure(
        "t1", "critical", policy, storage, hub, abort_on_failure=True,
    )
    assert result == FailureDecision.ABORT_GRAPH
    assert storage.update_task_status.call_count == 2


@pytest.mark.asyncio
async def test_cascade_skips_done_tasks():
    tasks = [
        {"id": "t1", "status": "failed", "depends_on": []},
        {"id": "t2", "status": "done", "depends_on": ["t1"]},
        {"id": "t3", "status": "pending", "depends_on": ["t1"]},
    ]
    storage = _make_storage(tasks=tasks)
    hub = _make_hub()
    blocked = await cascade_block_dependents("t1", storage, hub)
    assert blocked == ["t3"]
