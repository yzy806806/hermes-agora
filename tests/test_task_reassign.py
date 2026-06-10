"""Tests for parallel integration in task_status and reassign."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_exec import handle_task_status
from agora.coordinator.task_assign import reassign_task


@pytest.mark.asyncio
async def test_task_done_triggers_parallel_release():
    """When task is 'done' and parallel_coord set, release resources."""
    storage = AsyncMock()
    task = {"status": "running", "motion_id": "m1", "assigned_to": "a1"}
    storage.get_task.return_value = task
    hub = MagicMock()
    hub.send = AsyncMock()
    coord = MagicMock()
    coord._graph_tasks = {}
    coord._completed = set()
    coord._failed = set()
    coord._result = {"completed": [], "failed": [], "blocked": []}
    coord.agent_slots = {}
    coord.resource_tracker = MagicMock()
    coord.runqueue = MagicMock()
    with patch(
        "agora.coordinator.task_verify.verify_task",
        new_callable=AsyncMock,
    ), patch(
        "agora.coordinator.task_exec._parallel_on_done",
        new_callable=AsyncMock,
    ) as mock_done:
        await handle_task_status(
            "a1", {"task_id": "t1", "status": "done"},
            storage, hub, coord,
        )
        mock_done.assert_called_once()


@pytest.mark.asyncio
async def test_task_failed_triggers_parallel_cascade():
    """When task 'failed' and parallel_coord set, cascade failure."""
    storage = AsyncMock()
    task = {"status": "running", "motion_id": "m1"}
    storage.get_task.return_value = task
    hub = MagicMock()
    hub.send = AsyncMock()
    coord = MagicMock()
    with patch(
        "agora.coordinator.task_exec._parallel_on_fail",
        new_callable=AsyncMock,
    ) as mock_fail:
        await handle_task_status(
            "a1", {"task_id": "t1", "status": "failed", "error": "boom"},
            storage, hub, coord,
        )
        mock_fail.assert_called_once()


@pytest.mark.asyncio
async def test_reassign_task_picks_new_agent():
    """reassign_task finds a capable agent and sends assignment."""
    storage = AsyncMock()
    task = {
        "assigned_to": "a1", "required_capabilities": ["code"],
        "graph_id": "g1", "motion_id": "m1",
        "title": "T", "description": "", "depends_on": [],
    }
    storage.get_task.return_value = task
    storage.update_task_status = AsyncMock()
    hub = MagicMock()
    hub.get_online_agents.return_value = ["a2"]
    hub.send = AsyncMock(return_value=True)
    agent2 = {"agent_id": "a2", "capabilities": '["code"]'}
    storage.list_agents.return_value = [agent2]
    result = await reassign_task("t1", storage, hub)
    assert result == "a2"
    storage.update_task_status.assert_called_once()


@pytest.mark.asyncio
async def test_reassign_no_candidates():
    """reassign_task returns None when no capable agents available."""
    storage = AsyncMock()
    task = {
        "assigned_to": "a1", "required_capabilities": ["security"],
    }
    storage.get_task.return_value = task
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    storage.list_agents.return_value = []
    result = await reassign_task("t1", storage, hub)
    assert result is None
