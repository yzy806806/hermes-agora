"""Tests for TaskGenerator module."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coordinator.bootstrap.task_generator import (
    ASSIGNEE_MAP, TaskGenerator, TaskSpec,
)
from coordinator.bootstrap.discussion_driver import DiscussionResult


class TestTaskSpec:
    def test_defaults(self):
        spec = TaskSpec(
            title="Do X", description="Details", assignee="dev-merger",
        )
        assert spec.priority == 0
        assert spec.parent_task_id is None
        assert spec.skills == []
        assert spec.workspace_kind == "scratch"


class TestAssigneeMap:
    def test_known_categories(self):
        assert ASSIGNEE_MAP["development"] == "dev-merger"
        assert ASSIGNEE_MAP["review"] == "reviewer"
        assert ASSIGNEE_MAP["research"] == "planner"
        assert ASSIGNEE_MAP["release"] == "releaser"

    def test_infer_assignee_unknown(self):
        gen = TaskGenerator()
        assert gen._infer_assignee("unknown") == "dev-merger"


def _mock_post_response(resp):
    """Build a mock session where session.post returns resp via aenter."""
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=resp)
    post_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post = MagicMock(return_value=post_cm)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestTaskGenerator:
    def setup_method(self):
        self.gen = TaskGenerator(
            kanban_url="http://localhost:8000", board="test",
        )

    @pytest.mark.asyncio
    async def test_generate_tasks_empty(self):
        ids = await self.gen.generate_tasks({"action_items": []})
        assert ids == []

    @pytest.mark.asyncio
    async def test_generate_tasks_with_items(self):
        resp1 = AsyncMock()
        resp1.status = 200
        resp1.raise_for_status = MagicMock()
        resp1.json = AsyncMock(return_value={"task_id": "t1"})
        resp2 = AsyncMock()
        resp2.status = 200
        resp2.raise_for_status = MagicMock()
        resp2.json = AsyncMock(return_value={"task_id": "t2"})

        call_count = 0
        real_mock = _mock_post_response(resp1)

        def fake_client(*a, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_post_response(resp1)
            return _mock_post_response(resp2)

        with patch(
            "coordinator.bootstrap.task_generator.aiohttp.ClientSession",
            side_effect=fake_client,
        ):
            ids = await self.gen.generate_tasks({
                "action_items": [
                    {"title": "A", "description": "DA",
                     "category": "development"},
                    {"title": "B", "description": "DB",
                     "category": "review"},
                ],
            })
            assert ids == ["t1", "t2"]

    @pytest.mark.asyncio
    async def test_from_discussion_result(self):
        result = DiscussionResult(
            motion_id="m1", decision="adopted",
            recommended_actions=[
                {"title": "Build X", "category": "development"},
            ],
        )
        resp = AsyncMock()
        resp.status = 200
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value={"task_id": "t10"})

        with patch(
            "coordinator.bootstrap.task_generator.aiohttp.ClientSession",
            return_value=_mock_post_response(resp),
        ):
            ids = await self.gen.from_discussion_result(result)
            assert ids == ["t10"]

    @pytest.mark.asyncio
    async def test_create_task_failure(self):
        import aiohttp
        resp = AsyncMock()
        resp.status = 500
        resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(),
                status=500, message="Error",
            )
        )

        with patch(
            "coordinator.bootstrap.task_generator.aiohttp.ClientSession",
            return_value=_mock_post_response(resp),
        ):
            with pytest.raises(RuntimeError, match="Kanban task creation failed"):
                await self.gen._create_task(TaskSpec(
                    title="X", description="D", assignee="dev-merger",
                ))

    @pytest.mark.asyncio
    async def test_create_approval_task(self):
        resp = AsyncMock()
        resp.status = 200
        resp.raise_for_status = MagicMock()
        resp.json = AsyncMock(return_value={"task_id": "at1"})

        with patch(
            "coordinator.bootstrap.task_generator.aiohttp.ClientSession",
            return_value=_mock_post_response(resp),
        ):
            tid = await self.gen.create_approval_task("m1", "adopted")
            assert tid == "at1"
