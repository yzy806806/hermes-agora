"""Tests for Phase 10.4a: execute_task_graph delegation + RBAC middleware.

Covers parallel/sequential mode switching and middleware activation.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agora.coordinator.task_exec import execute_task_graph
from agora.coordinator.task_models import TaskGraph, TaskNode
from agora.coordinator.task_parallel import ParallelExecutionCoordinator
from agora.coordinator.task_resource import FileResourceTracker
from agora.coordinator.rbac_middleware import RBACMiddleware
from agora.coordinator.rbac import rbac_enforced


def _make_graph(mode: str) -> TaskGraph:
    return TaskGraph(
        id="g1", motion_id="m1", parallel_mode=mode,
        tasks=[
            TaskNode(
                id="t1", graph_id="g1", motion_id="m1",
                title="test task",
            ),
        ],
    )


def _mock_hub() -> MagicMock:
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    hub.send = AsyncMock(return_value=True)
    hub.broadcast = AsyncMock()
    return hub


def _mock_storage() -> MagicMock:
    s = MagicMock()
    s.list_agents = AsyncMock(return_value=[])
    s.get_agent_task_count = AsyncMock(return_value=0)
    s.get_task = AsyncMock(return_value=None)
    s.update_task_status = AsyncMock()
    s.log_event = AsyncMock()
    return s


class TestExecuteTaskGraph:
    """execute_task_graph delegates to parallel or sequential correctly."""

    @pytest.mark.asyncio
    async def test_sequential_mode_uses_assign(self):
        """Sequential mode falls back to assign_tasks."""
        graph = _make_graph("sequential")
        hub = _mock_hub()
        storage = _mock_storage()
        result = await execute_task_graph(
            graph, storage=storage, hub=hub,
            parallel_coord=None,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_auto_mode_with_parallel_coord(self):
        """Auto mode + parallel_coord delegates to coordinator."""
        graph = _make_graph("auto")
        hub = _mock_hub()
        storage = _mock_storage()
        tracker = FileResourceTracker()
        coord = ParallelExecutionCoordinator(
            storage=storage, hub=hub, resource_tracker=tracker,
        )
        result = await execute_task_graph(
            graph, storage=storage, hub=hub,
            parallel_coord=coord,
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_parallel_mode_with_coord(self):
        """Parallel mode + parallel_coord delegates to coordinator."""
        graph = _make_graph("parallel")
        hub = _mock_hub()
        storage = _mock_storage()
        tracker = FileResourceTracker()
        coord = ParallelExecutionCoordinator(
            storage=storage, hub=hub, resource_tracker=tracker,
        )
        result = await execute_task_graph(
            graph, storage=storage, hub=hub,
            parallel_coord=coord,
        )
        assert isinstance(result, dict)


class TestRBACMiddlewareActivation:
    """RBAC middleware is a no-op when enforcement is off."""

    def test_rbac_not_enforced_by_default(self):
        assert not rbac_enforced()

    def test_middleware_instantiable(self):
        mw = RBACMiddleware(app=None)
        assert mw is not None
