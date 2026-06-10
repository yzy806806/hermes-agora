"""Tests for Phase 10.1f: Parallel ↔ Task Engine integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_exec import (
    execute_task_graph, handle_task_status, handle_task_started,
)
from agora.coordinator.task_models import TaskGraph, TaskNode, TaskStatus


def _make_graph(mode="auto", tasks=None):
    t = tasks or [TaskNode(
        id="t1", graph_id="g1", motion_id="m1", title="T1")]
    return TaskGraph(
        id="g1", motion_id="m1", tasks=t, parallel_mode=mode)


@pytest.mark.asyncio
async def test_execute_sequential_fallback():
    """Sequential mode falls back to assign_tasks (Phase 9 compat)."""
    graph = _make_graph(mode="sequential")
    storage = AsyncMock()
    hub = MagicMock()
    coord = MagicMock()
    with patch(
        "agora.coordinator.task_assign.assign_tasks",
        new_callable=AsyncMock, return_value={"t1": "a1"},
    ) as mock_assign:
        result = await execute_task_graph(graph, storage, hub, coord)
        assert result == {"t1": "a1"}
        mock_assign.assert_called_once_with(graph, storage, hub)


@pytest.mark.asyncio
async def test_execute_parallel_delegates():
    """Non-sequential mode delegates to parallel_coord.execute_graph."""
    graph = _make_graph(mode="parallel")
    storage = AsyncMock()
    hub = MagicMock()
    coord = MagicMock()
    coord.execute_graph = AsyncMock(
        return_value={"graph_id": "g1", "completed": [], "failed": []})
    result = await execute_task_graph(graph, storage, hub, coord)
    coord.execute_graph.assert_called_once_with(graph)
    assert result["graph_id"] == "g1"


@pytest.mark.asyncio
async def test_execute_auto_uses_parallel():
    """Auto mode uses parallel coordinator when available."""
    graph = _make_graph(mode="auto")
    storage = AsyncMock()
    hub = MagicMock()
    coord = MagicMock()
    coord.execute_graph = AsyncMock(
        return_value={"graph_id": "g1", "completed": [], "failed": []})
    result = await execute_task_graph(graph, storage, hub, coord)
    coord.execute_graph.assert_called_once()


@pytest.mark.asyncio
async def test_execute_no_coord_falls_back():
    """No parallel_coord → sequential fallback regardless of mode."""
    graph = _make_graph(mode="parallel")
    storage = AsyncMock()
    hub = MagicMock()
    with patch(
        "agora.coordinator.task_assign.assign_tasks",
        new_callable=AsyncMock, return_value={},
    ) as mock_assign:
        result = await execute_task_graph(graph, storage, hub, None)
        mock_assign.assert_called_once()
