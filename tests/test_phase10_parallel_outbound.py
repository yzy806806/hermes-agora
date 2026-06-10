"""Tests for Phase 10 outbound parallel WS messages (task_parallel_ws.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.models import MessageType
from agora.coordinator.task_parallel_ws import (
    send_task_blocked,
    send_task_unblocked,
    send_task_retry,
    broadcast_graph_complete,
)


def _make_hub():
    hub = MagicMock()
    hub.send = AsyncMock()
    hub.broadcast = AsyncMock()
    return hub


@pytest.mark.asyncio
async def test_send_task_blocked():
    hub = _make_hub()
    await send_task_blocked(hub, "a1", "t1", "file conflict", ["t2"])
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["type"] == MessageType.TASK_BLOCKED.value
    assert msg["payload"]["task_id"] == "t1"
    assert msg["payload"]["reason"] == "file conflict"
    assert msg["payload"]["waiting_for"] == ["t2"]


@pytest.mark.asyncio
async def test_send_task_unblocked():
    hub = _make_hub()
    await send_task_unblocked(hub, "a1", "t1")
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["type"] == MessageType.TASK_UNBLOCKED.value
    assert msg["payload"]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_send_task_retry():
    hub = _make_hub()
    await send_task_retry(hub, "a1", "t1", "timeout", max_attempts=5)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["type"] == MessageType.TASK_RETRY.value
    assert msg["payload"]["max_attempts"] == 5


@pytest.mark.asyncio
async def test_broadcast_graph_complete():
    hub = _make_hub()
    summary = {"total": 5, "done": 3, "failed": 2}
    await broadcast_graph_complete(hub, "g1", summary)
    hub.broadcast.assert_called_once()
    msg = hub.broadcast.call_args[0][0]
    assert msg["type"] == MessageType.GRAPH_COMPLETE.value
    assert msg["payload"]["graph_id"] == "g1"
    assert msg["payload"]["summary"] == summary
