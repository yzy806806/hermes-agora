"""Tests for handle_task_accept_result from task_verify package."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.task_verify import handle_task_accept_result
from agora.coordinator.task_models import TaskStatus


@pytest.mark.asyncio
async def test_accept_result_accepted():
    storage = AsyncMock()
    storage.get_task.return_value = {
        "id": "t1", "status": TaskStatus.DONE.value,
    }
    hub = MagicMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": True}, storage, hub)
    storage.update_task_status.assert_called_once_with(
        "t1", TaskStatus.ACCEPTED.value)

@pytest.mark.asyncio
async def test_accept_result_rejected_requeues():
    storage = AsyncMock()
    storage.get_task.return_value = {
        "id": "t1", "status": TaskStatus.DONE.value,
    }
    hub = MagicMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": False,
                 "feedback": "needs work"}, storage, hub)
    calls = storage.update_task_status.call_args_list
    assert calls[0][0][0] == "t1"
    assert calls[0][0][1] == TaskStatus.REJECTED.value
    assert calls[0][1]["error_message"] == "needs work"
    assert calls[1][0][1] == TaskStatus.PENDING.value

@pytest.mark.asyncio
async def test_accept_result_task_not_found():
    storage = AsyncMock()
    storage.get_task.return_value = None
    hub = MagicMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": True}, storage, hub)
    storage.update_task_status.assert_not_called()
