"""Tests for task_verify — auto-verify logic and review delegation."""

import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_verify import (
    verify_task, _auto_verify, _is_simple_task,
    _delegate_review, handle_task_accept_result,
)
from agora.coordinator.task_models import TaskStatus


def _make_task(tid="t1", status="done", caps=None,
               artifacts=None, deps=None):
    caps = caps or ["code"]
    artifacts = artifacts or []
    deps = deps or []
    return {
        "id": tid, "graph_id": "g1", "motion_id": "m1",
        "title": "Test task", "description": "desc",
        "status": status, "assigned_to": "a1",
        "required_capabilities": caps,
        "depends_on": deps,
        "artifact_paths": artifacts,
        "error_message": None,
    }


def _make_agent(aid, caps, online=True):
    caps_json = json.dumps(caps)
    return {"agent_id": aid, "capabilities": caps_json}


# --- _auto_verify ---

@pytest.mark.asyncio
async def test_auto_verify_all_present():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        path = f.name
    try:
        task = _make_task(artifacts=[path])
        passed, reason = await _auto_verify(task)
        assert passed is True
        assert "present" in reason
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_auto_verify_missing_artifact():
    task = _make_task(artifacts=["/nonexistent/file.py"])
    passed, reason = await _auto_verify(task)
    assert passed is False
    assert "Missing" in reason


@pytest.mark.asyncio
async def test_auto_verify_no_artifacts():
    task = _make_task(artifacts=[])
    passed, reason = await _auto_verify(task)
    assert passed is True
    assert "No artifacts" in reason


# --- _is_simple_task ---

def test_simple_single_code_artifact():
    task = _make_task(caps=["code"], artifacts=["f.py"])
    assert _is_simple_task(task) is True


def test_simple_docs_only():
    task = _make_task(caps=["docs"], artifacts=["f.md"])
    assert _is_simple_task(task) is True


def test_not_simple_security():
    task = _make_task(caps=["security"], artifacts=["f.py"])
    assert _is_simple_task(task) is False


def test_not_simple_deploy():
    task = _make_task(caps=["deploy"], artifacts=[])
    assert _is_simple_task(task) is False


def test_not_simple_multiple_artifacts():
    task = _make_task(caps=["code"], artifacts=["a.py", "b.py"])
    assert _is_simple_task(task) is False


def test_not_simple_no_caps():
    task = _make_task(caps=[], artifacts=["f.py"])
    assert _is_simple_task(task) is False


# --- verify_task ---

@pytest.mark.asyncio
async def test_verify_auto_accepts_simple():
    task = _make_task(caps=["code"], artifacts=[])
    storage = AsyncMock()
    storage.get_task.return_value = task
    hub = MagicMock()
    await verify_task("t1", storage, hub)
    storage.update_task_status.assert_called_once_with(
        "t1", TaskStatus.ACCEPTED.value)


@pytest.mark.asyncio
async def test_verify_delegates_complex():
    task = _make_task(caps=["security"], artifacts=["f.py"])
    storage = AsyncMock()
    storage.get_task.return_value = task
    storage.list_agents.return_value = [
        _make_agent("r1", ["review"]),
    ]
    hub = MagicMock()
    hub.get_online_agents.return_value = ["r1"]
    hub.send = AsyncMock(return_value=True)
    await verify_task("t1", storage, hub)
    hub.send.assert_called_once()


@pytest.mark.asyncio
async def test_verify_task_not_found():
    storage = AsyncMock()
    storage.get_task.return_value = None
    hub = MagicMock()
    await verify_task("t1", storage, hub)
    storage.update_task_status.assert_not_called()


# --- _delegate_review ---

@pytest.mark.asyncio
async def test_delegate_sends_to_reviewer():
    task = _make_task()
    storage = AsyncMock()
    storage.list_agents.return_value = [
        _make_agent("r1", ["review"]),
    ]
    hub = MagicMock()
    hub.get_online_agents.return_value = ["r1"]
    hub.send = AsyncMock(return_value=True)
    await _delegate_review(task, storage, hub)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["type"] == "TASK_VERIFY"


@pytest.mark.asyncio
async def test_delegate_no_reviewer():
    task = _make_task()
    storage = AsyncMock()
    storage.list_agents.return_value = []
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    await _delegate_review(task, storage, hub)
    hub.send.assert_not_called()


# --- handle_task_accept_result ---

@pytest.mark.asyncio
async def test_accept_result_accepted():
    task = _make_task(status="done")
    storage = AsyncMock()
    storage.get_task.return_value = task
    await handle_task_accept_result(
        "r1", {"task_id": "t1", "accepted": True,
               "feedback": "LGTM"}, storage, MagicMock())
    storage.update_task_status.assert_called_with(
        "t1", TaskStatus.ACCEPTED.value)


@pytest.mark.asyncio
async def test_accept_result_rejected():
    task = _make_task(status="done")
    storage = AsyncMock()
    storage.get_task.return_value = task
    await handle_task_accept_result(
        "r1", {"task_id": "t1", "accepted": False,
               "feedback": "Bad code"}, storage, MagicMock())
    calls = storage.update_task_status.call_args_list
    assert calls[0][0][0] == "t1"
    assert calls[0][0][1] == TaskStatus.REJECTED.value
    assert calls[1][0][1] == TaskStatus.PENDING.value
