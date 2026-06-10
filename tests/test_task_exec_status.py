"""Tests for task_exec.py — state machine and WS handlers (part 2)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_exec import handle_task_status
from agora.coordinator.task_verify import handle_task_accept_result
from agora.coordinator.task_models import TaskStatus


@pytest.mark.asyncio
async def test_status_invalid_transition():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "pending", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status("a1", {"task_id": "t1", "status": "done"},
                             storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "invalid_transition"

@pytest.mark.asyncio
async def test_status_done_triggers_verify():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "running", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    with patch("agora.coordinator.task_verify.verify_task",
               new_callable=AsyncMock) as mock_verify:
        await handle_task_status(
            "a1", {"task_id": "t1", "status": "done"}, storage, hub)
        mock_verify.assert_called_once_with("t1", storage, hub)

@pytest.mark.asyncio
async def test_status_failed_logs_event():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "running", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status(
        "a1", {"task_id": "t1", "status": "failed", "error": "boom"},
        storage, hub)
    storage.log_event.assert_called_once_with(
        "task.failed", "Task t1 failed: boom",
        motion_id="m1", agent_id="a1")

@pytest.mark.asyncio
async def test_status_missing_status():
    storage = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status("a1", {"task_id": "t1"}, storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "missing_status"
