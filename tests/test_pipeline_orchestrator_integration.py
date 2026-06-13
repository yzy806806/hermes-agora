"""Integration tests for PipelineOrchestrator.run() (Phase 13.1b)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agora.coordinator.pipeline import PipelineOrchestrator
from agora.coordinator.pipeline_models import PipelinePhase
from agora.coordinator.bootstrap.discussion_driver import DiscussionResult


def _make_discussion_result(decision="adopted"):
    return DiscussionResult(
        motion_id="motion-1", decision=decision,
        recommended_actions=[
            {"title": "Task 1", "description": "Do thing", "category": "dev"},
        ],
    )


def _make_orchestrator():
    storage = MagicMock()
    hub = MagicMock()
    hub.get_online_agents.return_value = ["reviewer-1", "releaser-1"]
    hub.send = AsyncMock(return_value=True)
    bootstrap = MagicMock()
    bootstrap.discussion_driver = MagicMock()
    bootstrap.discussion_driver.start_dev_discussion = AsyncMock(
        return_value="motion-1",
    )
    result = _make_discussion_result()
    bootstrap.discussion_driver.wait_for_result = AsyncMock(
        return_value=result,
    )
    bootstrap.task_generator = MagicMock()
    bootstrap.task_generator.from_discussion_result = AsyncMock(
        return_value=["task-1"],
    )
    parallel = MagicMock()
    parallel.execute_graph = AsyncMock(return_value={
        "completed": ["task-1"], "failed": [],
    })
    return PipelineOrchestrator(storage, hub, bootstrap, parallel)


class TestOrchestratorRun:
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        orch = _make_orchestrator()
        run = await orch.run("Build a REST API", "proj-1")
        assert run.phase == PipelinePhase.COMPLETED
        assert run.motion_id == "motion-1"
        assert run.tasks_total == 1
        assert run.tasks_completed == 1
        assert run.review_outcome == "approved"
        assert run.release_version is not None
        assert run.error is None

    @pytest.mark.asyncio
    async def test_discussion_rejected(self):
        orch = _make_orchestrator()
        result = _make_discussion_result(decision="rejected")
        orch.bootstrap.discussion_driver.wait_for_result = AsyncMock(
            return_value=result,
        )
        run = await orch.run("Bad idea", "proj-2")
        assert run.phase == PipelinePhase.FAILED
        assert run.error is not None

    @pytest.mark.asyncio
    async def test_pipeline_stored_in_dict(self):
        orch = _make_orchestrator()
        run = await orch.run("Idea", "proj-3")
        assert run.id in orch.pipelines
        assert orch.pipelines[run.id] is run
