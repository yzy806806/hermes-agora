"""Tests for Phase 10 parallel WS handlers (task_exec + task_parallel_ws)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.task_exec import (
    handle_task_started,
    handle_task_progress,
)
from agora.coordinator.task_parallel_ws import (
    send_task_blocked,
    send_task_unblocked,
    send_task_retry,
    broadcast_graph_complete,
)


# --- handle_task_started ---

@pytest.mark.asyncio
async def test_task_started_missing_task_id():
    storage = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_started("a1", {}, storage, hub)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "missing_task_id"


@pytest.mark.asyncio
async def test_task_started_task_not_found():
    storage = AsyncMock()
    storage.get_task.return_value = None
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_started("a1", {"task_id": "t1"}, storage, hub)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "task_not_found"


@pytest.mark.asyncio
async def test_task_started_success():
    storage = AsyncMock()
    storage.get_task.return_value = {"motion_id": "m1", "status": "assigned"}
    storage.update_task_status = AsyncMock()
    storage.log_event = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_started("a1", {"task_id": "t1"}, storage, hub)
    storage.update_task_status.assert_called_once_with("t1", "running")
    assert storage.log_event.call_count == 1


# --- handle_task_progress ---

@pytest.mark.asyncio
async def test_task_progress_missing_task_id():
    storage = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_progress("a1", {}, storage, hub)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "missing_task_id"


@pytest.mark.asyncio
async def test_task_progress_success():
    storage = AsyncMock()
    storage.log_event = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    payload = {"task_id": "t1", "progress_pct": 50, "message": "halfway"}
    await handle_task_progress("a1", payload, storage, hub)
    storage.log_event.assert_called_once()
    event_msg = storage.log_event.call_args[0][1]
    assert "50%" in event_msg
    assert "halfway" in event_msg
