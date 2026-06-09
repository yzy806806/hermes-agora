"""Tests for Task status updates and agent task count."""

import pytest
import pytest_asyncio

from agora.coordinator.storage import Storage
from agora.coordinator.task_models import TaskNode


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_task_status.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest_asyncio.fixture(loop_scope="session")
async def task_env(storage):
    """Create agent, motion, graph, and one task for status tests."""
    await storage.register_agent("ag1", "Agent1", "gpt-4")
    motion = await storage.create_motion("Motion", "desc")
    mid = motion["id"]
    await storage.create_task_graph("g1", mid)
    task = TaskNode(
        id="t1", graph_id="g1", motion_id=mid,
        title="Task 1", required_capabilities=["code"],
    )
    await storage.create_task(task)
    return storage, mid


@pytest.mark.asyncio
async def test_update_task_status_assigned(task_env):
    s, _ = task_env
    await s.update_task_status("t1", "assigned", assigned_to="ag1")
    task = await s.get_task("t1")
    assert task["status"] == "assigned"
    assert task["assigned_to"] == "ag1"


@pytest.mark.asyncio
async def test_update_task_status_running(task_env):
    s, _ = task_env
    await s.update_task_status("t1", "running")
    task = await s.get_task("t1")
    assert task["status"] == "running"
    assert task["started_at"] is not None


@pytest.mark.asyncio
async def test_update_task_status_done(task_env):
    s, _ = task_env
    await s.update_task_status("t1", "done", artifact_paths=["/tmp/out"])
    task = await s.get_task("t1")
    assert task["status"] == "done"
    assert task["completed_at"] is not None
    assert task["artifact_paths"] == ["/tmp/out"]


@pytest.mark.asyncio
async def test_update_task_status_failed(task_env):
    s, _ = task_env
    await s.update_task_status(
        "t1", "failed", error_message="timeout"
    )
    task = await s.get_task("t1")
    assert task["status"] == "failed"
    assert task["error_message"] == "timeout"
    assert task["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_agent_task_count(task_env):
    s, _ = task_env
    await s.update_task_status("t1", "assigned", assigned_to="ag1")
    count = await s.get_agent_task_count("ag1", active_only=True)
    assert count == 1

    count2 = await s.get_agent_task_count("nonexistent")
    assert count2 == 0


@pytest.mark.asyncio
async def test_get_agent_task_count_all(task_env):
    s, _ = task_env
    await s.update_task_status("t1", "assigned", assigned_to="ag1")
    await s.update_task_status("t1", "done")

    active = await s.get_agent_task_count("ag1", active_only=True)
    assert active == 0

    total = await s.get_agent_task_count("ag1", active_only=False)
    assert total == 1
