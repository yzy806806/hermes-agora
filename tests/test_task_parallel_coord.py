"""Tests for ParallelExecutionCoordinator."""

import asyncio
import pytest

from agora.coordinator.task_models import TaskGraph, TaskNode, TaskStatus
from agora.coordinator.task_resource import FileResourceTracker
from agora.coordinator.task_parallel import ParallelExecutionCoordinator


class MockStorage:
    """Minimal mock storage for coordinator tests."""
    def __init__(self):
        self._tasks: dict = {}
        self._agents: dict = {}

    async def update_task_status(self, task_id, status, **kw):
        self._tasks[task_id] = {"status": status, **kw}

    async def get_agent_task_count(self, agent_id, active_only=True):
        return 0

    async def list_agents(self, online_only=False):
        return list(self._agents.values())


class MockHub:
    """Minimal mock hub for coordinator tests."""
    def __init__(self):
        self.sent: list = []

    async def send(self, agent_id, msg):
        self.sent.append((agent_id, msg))
        return True

    def get_online_agents(self):
        return ["agent1"]


class TestParallelExecutionCoordinator:
    @pytest.fixture
    def coord(self):
        storage = MockStorage()
        hub = MockHub()
        storage._agents["agent1"] = {
            "agent_id": "agent1", "capabilities": ["code"],
            "max_concurrent_tasks": 2,
        }
        return ParallelExecutionCoordinator(storage, hub)

    @pytest.mark.asyncio
    async def test_empty_graph(self, coord):
        graph = TaskGraph(id="g1", motion_id="m1", tasks=[])
        result = await coord.execute_graph(graph)
        assert result["graph_id"] == "g1"
        assert result["completed"] == []
        assert result["failed"] == []

    @pytest.mark.asyncio
    async def test_single_task_no_deps(self, coord):
        task = TaskNode(
            id="t1", graph_id="g1", motion_id="m1",
            title="Test task", required_capabilities=["code"],
        )
        graph = TaskGraph(id="g1", motion_id="m1", tasks=[task])
        result = await coord.execute_graph(graph)
        assert "t1" in result["completed"]

    @pytest.mark.asyncio
    async def test_two_independent_tasks(self, coord):
        t1 = TaskNode(
            id="t1", graph_id="g1", motion_id="m1",
            title="Task 1", required_capabilities=["code"],
        )
        t2 = TaskNode(
            id="t2", graph_id="g1", motion_id="m1",
            title="Task 2", required_capabilities=["code"],
        )
        graph = TaskGraph(id="g1", motion_id="m1", tasks=[t1, t2])
        result = await coord.execute_graph(graph)
        assert "t1" in result["completed"]
        assert "t2" in result["completed"]
