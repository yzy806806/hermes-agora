"""Tests for task_verify — auto-verify and simple-task checks."""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.task_verify import (
    verify_task, is_simple_task, auto_verify,
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


@pytest.mark.asyncio
async def test_auto_verify_all_present():
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        path = f.name
    try:
        passed, reason = await auto_verify(_make_task(artifacts=[path]))
        assert passed and "present" in reason
    finally:
        os.unlink(path)

@pytest.mark.asyncio
async def test_auto_verify_missing():
    p, r = await auto_verify(_make_task(artifacts=["/no/file.py"]))
    assert not p and "Missing" in r

@pytest.mark.asyncio
async def test_auto_verify_no_artifacts():
    p, r = await auto_verify(_make_task(artifacts=[]))
    assert p and "No artifacts" in r


@pytest.mark.asyncio
async def test_simple_code():
    assert await is_simple_task(
        _make_task(caps=["code"], artifacts=["f.py"]))

@pytest.mark.asyncio
async def test_simple_docs():
    assert await is_simple_task(
        _make_task(caps=["docs"], artifacts=["f.md"]))

@pytest.mark.asyncio
async def test_not_simple_security():
    assert not await is_simple_task(_make_task(caps=["security"]))

@pytest.mark.asyncio
async def test_not_simple_deploy():
    assert not await is_simple_task(_make_task(caps=["deploy"]))

@pytest.mark.asyncio
async def test_not_simple_multi_artifact():
    assert not await is_simple_task(
        _make_task(caps=["code"], artifacts=["a.py", "b.py"]))

@pytest.mark.asyncio
async def test_not_simple_no_caps():
    assert not await is_simple_task(_make_task(caps=[]))


@pytest.mark.asyncio
async def test_simple_with_deps_all_accepted():
    """Deps all ACCEPTED → still simple."""
    storage = AsyncMock()
    storage.get_task.return_value = _make_task(
        tid="dep1", status="accepted")
    task = _make_task(caps=["code"], artifacts=["f.py"], deps=["dep1"])
    assert await is_simple_task(task, storage)

@pytest.mark.asyncio
async def test_not_simple_with_unmet_dep():
    """Dep not ACCEPTED → not simple."""
    storage = AsyncMock()
    storage.get_task.return_value = _make_task(
        tid="dep1", status="done")
    task = _make_task(caps=["code"], artifacts=["f.py"], deps=["dep1"])
    assert not await is_simple_task(task, storage)

@pytest.mark.asyncio
async def test_simple_with_dep_not_found():
    """Dep not found in storage → treated as met (no blocking dep)."""
    storage = AsyncMock()
    storage.get_task.return_value = None
    task = _make_task(caps=["code"], artifacts=["f.py"], deps=["dep1"])
    assert await is_simple_task(task, storage)


@pytest.mark.asyncio
async def test_verify_auto_accepts():
    storage = AsyncMock()
    storage.get_task.return_value = _make_task(caps=["code"], artifacts=[])
    await verify_task("t1", storage, MagicMock())
    storage.update_task_status.assert_called_once_with(
        "t1", TaskStatus.ACCEPTED.value)

@pytest.mark.asyncio
async def test_verify_not_found():
    storage = AsyncMock()
    storage.get_task.return_value = None
    await verify_task("t1", storage, MagicMock())
    storage.update_task_status.assert_not_called()
