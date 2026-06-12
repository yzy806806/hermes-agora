"""Tests for HermesAdapter — kanban task mapping and discussion routing."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from agora_agent_sdk.protocol import TaskNode
from agora_hermes_bridge.adapter import HermesAdapter
from agora_hermes_bridge.cli import run_hermes


@pytest.fixture
def adapter(mock_client, profile):
    """Create HermesAdapter with mocked hermes CLI."""
    with patch("agora_hermes_bridge.adapter.hermes_available", return_value=True):
        return HermesAdapter(mock_client, profile.name, poll_interval=1, poll_max=2)


class TestHermesAdapterInit:
    def test_creates_with_profile(self, adapter, profile):
        assert adapter.profile == profile.name
        assert adapter._kanban_map == {}

    def test_raises_without_hermes_cli(self, mock_client, profile):
        with patch("agora_hermes_bridge.adapter.hermes_available", return_value=False):
            with pytest.raises(RuntimeError, match="hermes.*not found"):
                HermesAdapter(mock_client, profile.name)


class TestTaskAssignedMapping:
    @pytest.mark.asyncio
    async def test_creates_kanban_task(self, adapter, mock_client, sample_task):
        kanban_result = {"task_id": "kb_001"}
        with patch.object(
            adapter, "_poll_interval", 0
        ), patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value=kanban_result,
        ), patch(
            "agora_hermes_bridge.adapter.poll_kanban_task",
            new_callable=AsyncMock,
        ):
            await adapter.on_task_assigned(sample_task)
        mock_client.report_task_start.assert_awaited_once_with(sample_task.task_id)
        assert adapter._kanban_map[sample_task.task_id] == "kb_001"

    @pytest.mark.asyncio
    async def test_handles_empty_kanban_id(self, adapter, mock_client, sample_task):
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value={},
        ):
            await adapter.on_task_assigned(sample_task)
        mock_client.report_task_start.assert_not_awaited()


class TestDiscussionMessageRouting:
    @pytest.mark.asyncio
    async def test_forwards_discussion_to_hermes(self, adapter):
        adapter._kanban_map["motion-1"] = "kb_045"
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value={},
        ) as mock_run:
            await adapter.on_discussion_message("motion-1", "I vote yes")
        mock_run.assert_awaited_once()
        call_args = mock_run.call_args[0][0]
        assert "kanban" in call_args
        assert "comment" in call_args

    @pytest.mark.asyncio
    async def test_discussion_without_kanban_map(self, adapter):
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value={},
        ) as mock_run:
            await adapter.on_discussion_message("unknown-motion", "Hello")
        mock_run.assert_awaited_once()


class TestDevilsAdvocate:
    @pytest.mark.asyncio
    async def test_returns_hermes_response(self, adapter):
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock,
            return_value={"response": "Counter-argument here"},
        ):
            result = await adapter.on_devils_advocate("m-1", "Should we refactor?")
        assert result == "Counter-argument here"

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self, adapter):
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value={},
        ):
            result = await adapter.on_devils_advocate("m-1", "topic")
        assert result == ""
