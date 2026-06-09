"""Tests for Task CRUD storage operations."""

import pytest
import pytest_asyncio

from agora.coordinator.storage import Storage
from agora.coordinator.task_models import TaskNode, TaskStatus


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_task_crud.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest.mark.asyncio
async def test_create_and_get_task_graph(storage):
    await storage.register_agent("ag1", "Agent1", "gpt-4")
    motion = await storage.create_motion("Test Motion", "desc")
    mid = motion["id"]

    result = await storage.create_task_graph("g1", mid)
    assert result["id"] == "g1"
    assert result["motion_id"] == mid

    graph = await storage.get_task_graph("g1")
    assert graph is not None
    assert graph["id"] == "g1"
    assert graph["tasks"] == []


@pytest.mark.asyncio
async def test_get_task_graph_by_motion(storage):
    motion = await storage.create_motion("Motion2", "desc2")
    mid = motion["id"]
    await storage.create_task_graph("g2", mid)

    graph = await storage.get_task_graph_by_motion(mid)
    assert graph is not None
    assert graph["motion_id"] == mid


@pytest.mark.asyncio
async def test_get_task_graph_not_found(storage):
    assert await storage.get_task_graph("nonexistent") is None


@pytest.mark.asyncio
async def test_create_and_get_task(storage):
    motion = await storage.create_motion("Motion3", "desc3")
    mid = motion["id"]
    await storage.create_task_graph("g3", mid)

    task = TaskNode(
        id="t1", graph_id="g3", motion_id=mid,
        title="Task 1", description="Do stuff",
        required_capabilities=["code", "test"],
        depends_on=[], artifact_paths=[],
    )
    result = await storage.create_task(task)
    assert result["id"] == "t1"
    assert result["status"] == "pending"

    fetched = await storage.get_task("t1")
    assert fetched is not None
    assert fetched["title"] == "Task 1"
    assert fetched["required_capabilities"] == ["code", "test"]


@pytest.mark.asyncio
async def test_list_tasks_with_filters(storage):
    motion = await storage.create_motion("Motion4", "desc4")
    mid = motion["id"]
    await storage.create_task_graph("g4", mid)

    t1 = TaskNode(id="t2", graph_id="g4", motion_id=mid, title="T2")
    t2 = TaskNode(id="t3", graph_id="g4", motion_id=mid, title="T3")
    await storage.create_task(t1)
    await storage.create_task(t2)

    all_tasks = await storage.list_tasks(graph_id="g4")
    assert len(all_tasks) == 2

    by_status = await storage.list_tasks(status="pending")
    assert len(by_status) >= 2
