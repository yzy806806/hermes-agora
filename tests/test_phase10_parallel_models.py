"""Tests for Phase 10 parallel execution models + storage."""

import pytest
import pytest_asyncio

from agora.coordinator.storage import Storage
from agora.coordinator.task_models import (
    ExecutionSlot, ResourceLock, TaskGraph, TaskNode,
)


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_parallel.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


# --- Model tests ---

def test_execution_slot_defaults():
    slot = ExecutionSlot(task_id="t1", agent_id="a1")
    assert slot.status == "running"
    assert slot.started_at is not None


def test_resource_lock_defaults():
    lock = ResourceLock(
        resource_path="src/main.py", locked_by="t1",
    )
    assert lock.lock_type == "write"
    assert lock.waiting_tasks == []
    assert lock.acquired_at is not None


def test_task_graph_parallel_defaults():
    graph = TaskGraph(id="g1", motion_id="m1")
    assert graph.parallel_mode == "auto"
    assert graph.max_parallel_slots == 10
    assert graph.resource_conflict_policy == "warn"


def test_task_graph_parallel_custom():
    graph = TaskGraph(
        id="g2", motion_id="m2",
        parallel_mode="parallel",
        max_parallel_slots=5,
        resource_conflict_policy="abort",
    )
    assert graph.parallel_mode == "parallel"


# --- ExecutionSlot CRUD tests ---

@pytest.mark.asyncio
async def test_create_and_get_execution_slot(storage):
    await storage.register_agent("a1", "Agent1", "gpt-4")
    motion = await storage.create_motion("M1", "desc")
    await storage.create_task_graph("g1", motion["id"])
    task = TaskNode(
        id="t1", graph_id="g1", motion_id=motion["id"],
        title="T1",
    )
    await storage.create_task(task)

    slot = ExecutionSlot(task_id="t1", agent_id="a1")
    result = await storage.create_execution_slot(slot)
    assert result["task_id"] == "t1"
    assert result["status"] == "running"

    slots = await storage.get_execution_slots(agent_id="a1")
    assert len(slots) >= 1
    assert slots[0]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_update_slot_status(storage):
    await storage.register_agent("a2", "Agent2", "gpt-4")
    motion = await storage.create_motion("M2", "desc")
    await storage.create_task_graph("g2", motion["id"])
    task = TaskNode(
        id="t2", graph_id="g2", motion_id=motion["id"],
        title="T2",
    )
    await storage.create_task(task)
    slot = ExecutionSlot(task_id="t2", agent_id="a2")
    await storage.create_execution_slot(slot)
    await storage.update_slot_status("t2", "completing")
    slots = await storage.get_execution_slots(status="completing")
    assert any(s["task_id"] == "t2" for s in slots)


# --- ResourceLock CRUD tests ---

@pytest.mark.asyncio
async def test_acquire_and_get_resource_lock(storage):
    await storage.register_agent("a3", "Agent3", "gpt-4")
    motion = await storage.create_motion("M3", "desc")
    await storage.create_task_graph("g3", motion["id"])
    task = TaskNode(
        id="t3", graph_id="g3", motion_id=motion["id"],
        title="T3",
    )
    await storage.create_task(task)

    lock = ResourceLock(
        resource_path="src/parallel_new.py", locked_by="t3",
    )
    result = await storage.acquire_resource_lock(lock)
    assert result["resource_path"] == "src/parallel_new.py"
    assert result["locked_by"] == "t3"

    fetched = await storage.get_resource_lock("src/parallel_new.py")
    assert fetched is not None
    assert fetched["lock_type"] == "write"


@pytest.mark.asyncio
async def test_add_waiting_task_and_release(storage):
    await storage.register_agent("a4", "Agent4", "gpt-4")
    motion = await storage.create_motion("M4", "desc")
    await storage.create_task_graph("g4", motion["id"])
    task = TaskNode(
        id="t4", graph_id="g4", motion_id=motion["id"],
        title="T4",
    )
    await storage.create_task(task)

    lock = ResourceLock(
        resource_path="src/waiting.py", locked_by="t4",
        waiting_tasks=["t5"],
    )
    await storage.acquire_resource_lock(lock)
    await storage.add_waiting_task("src/waiting.py", "t6")
    fetched = await storage.get_resource_lock("src/waiting.py")
    assert "t5" in fetched["waiting_tasks"]
    assert "t6" in fetched["waiting_tasks"]
    await storage.release_all_locks_for_task("t4")
    assert await storage.get_resource_lock("src/waiting.py") is None


@pytest.mark.asyncio
async def test_task_graph_parallel_fields(storage):
    motion = await storage.create_motion("M5", "desc")
    result = await storage.create_task_graph(
        "g5", motion["id"],
        parallel_mode="parallel",
        max_parallel_slots=3,
        resource_conflict_policy="queue",
    )
    assert result["parallel_mode"] == "parallel"
    assert result["max_parallel_slots"] == 3
    assert result["resource_conflict_policy"] == "queue"
