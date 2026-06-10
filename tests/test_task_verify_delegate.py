"""Tests for task_verify — review delegation and accept-result handler."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.task_verify import (
    verify_task, delegate_review, handle_task_accept_result,
)
from agora.coordinator.task_models import TaskStatus

def _make_task(tid="t1", status="done", caps=None,
               artifacts=None, deps=None):
    caps = caps if caps is not None else ["code"]
    artifacts = artifacts if artifacts is not None else []
    deps = deps if deps is not None else []
    return dict(id=tid, graph_id="g1", motion_id="m1", title="Test",
                description="desc", status=status, assigned_to="a1",
                required_capabilities=caps, depends_on=deps,
                artifact_paths=artifacts, error_message=None)

def _make_agent(aid, caps):
    return {"agent_id": aid, "capabilities": json.dumps(caps)}


@pytest.mark.asyncio
async def test_verify_delegates_complex():
    task = _make_task(caps=["security"], artifacts=["f.py"])
    storage = AsyncMock()
    storage.get_task.return_value = task
    storage.list_agents.return_value = [_make_agent("r1", ["review"])]
    hub = MagicMock()
    hub.get_online_agents.return_value = ["r1"]
    hub.send = AsyncMock(return_value=True)
    await verify_task("t1", storage, hub)
    hub.send.assert_called_once()

@pytest.mark.asyncio
async def test_delegate_sends_to_reviewer():
    storage = AsyncMock()
    storage.list_agents.return_value = [_make_agent("r1", ["review"])]
    hub = MagicMock()
    hub.get_online_agents.return_value = ["r1"]
    hub.send = AsyncMock(return_value=True)
    await delegate_review(_make_task(), storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["type"] == "TASK_VERIFY"


@pytest.mark.asyncio
async def test_delegate_no_reviewer():
    storage = AsyncMock()
    storage.list_agents.return_value = []
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    await delegate_review(_make_task(), storage, hub)
    hub.send.assert_not_called()


@pytest.mark.asyncio
async def test_accept_result_accepted():
    storage = AsyncMock()
    storage.get_task.return_value = _make_task()
    await handle_task_accept_result(
        "r1", {"task_id": "t1", "accepted": True,
               "feedback": "LGTM"}, storage, MagicMock())
    storage.update_task_status.assert_called_with(
        "t1", TaskStatus.ACCEPTED.value)


@pytest.mark.asyncio
async def test_accept_result_rejected():
    storage = AsyncMock()
    storage.get_task.return_value = _make_task()
    await handle_task_accept_result(
        "r1", {"task_id": "t1", "accepted": False,
               "feedback": "Bad"}, storage, MagicMock())
    calls = storage.update_task_status.call_args_list
    assert calls[0][0][1] == TaskStatus.REJECTED.value
    assert calls[1][0][1] == TaskStatus.PENDING.value
