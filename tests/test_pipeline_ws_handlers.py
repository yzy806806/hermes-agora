"""Tests for Phase 13.1f: Pipeline WS message handlers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agora.coordinator.models import MessageType
from agora.coordinator.ws_handlers import (
    handle_pipeline_phase_change,
    handle_pipeline_task_update,
    handle_pipeline_completed,
    handle_pipeline_error,
)


@pytest.mark.asyncio
async def test_pipeline_phase_change_publishes():
    """PIPELINE_PHASE_CHANGE publishes to pipelines channel."""
    with patch("agora.coordinator.event_bus.publish", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = 1
        result = await handle_pipeline_phase_change(
            pipeline_id="pl-1",
            phase="executing",
            project_id="proj-1",
            prev_phase="discussing",
        )
    assert result == 1
    mock_pub.assert_awaited_once()
    args = mock_pub.call_args
    assert args[0][0] == "PIPELINE_PHASE_CHANGE"
    assert args[1]["channel"] == "pipelines"
    payload = args[0][1]
    assert payload["pipeline_id"] == "pl-1"
    assert payload["phase"] == "executing"
    assert payload["previous_phase"] == "discussing"
    assert payload["project_id"] == "proj-1"


@pytest.mark.asyncio
async def test_pipeline_task_update_publishes():
    """PIPELINE_TASK_UPDATE publishes to pipelines channel."""
    with patch("agora.coordinator.event_bus.publish", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = 2
        result = await handle_pipeline_task_update(
            pipeline_id="pl-1",
            task_id="t-42",
            status="completed",
            project_id="proj-1",
            agent_id="agent-a",
        )
    assert result == 2
    args = mock_pub.call_args
    assert args[0][0] == "PIPELINE_TASK_UPDATE"
    assert args[1]["channel"] == "pipelines"
    payload = args[0][1]
    assert payload["task_id"] == "t-42"
    assert payload["status"] == "completed"
    assert payload["agent_id"] == "agent-a"


@pytest.mark.asyncio
async def test_pipeline_completed_publishes():
    """PIPELINE_COMPLETED publishes to pipelines channel."""
    with patch("agora.coordinator.event_bus.publish", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = 1
        result = await handle_pipeline_completed(
            pipeline_id="pl-1",
            project_id="proj-1",
            tasks_total=5,
            tasks_completed=4,
            tasks_failed=1,
            release_version="v0.13.0",
        )
    assert result == 1
    args = mock_pub.call_args
    assert args[0][0] == "PIPELINE_COMPLETED"
    assert args[1]["channel"] == "pipelines"
    payload = args[0][1]
    assert payload["tasks_total"] == 5
    assert payload["release_version"] == "v0.13.0"


@pytest.mark.asyncio
async def test_pipeline_error_publishes():
    """PIPELINE_ERROR publishes to pipelines channel."""
    with patch("agora.coordinator.event_bus.publish", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = 1
        result = await handle_pipeline_error(
            pipeline_id="pl-1",
            project_id="proj-1",
            error="LLM timeout",
            phase="decomposing",
        )
    assert result == 1
    args = mock_pub.call_args
    assert args[0][0] == "PIPELINE_ERROR"
    assert args[1]["channel"] == "pipelines"
    payload = args[0][1]
    assert payload["error"] == "LLM timeout"
    assert payload["phase"] == "decomposing"


@pytest.mark.asyncio
async def test_pipeline_message_types_exist():
    """All PIPELINE_* MessageType values are defined."""
    assert MessageType.PIPELINE_PHASE_CHANGE.value == "PIPELINE_PHASE_CHANGE"
    assert MessageType.PIPELINE_TASK_UPDATE.value == "PIPELINE_TASK_UPDATE"
    assert MessageType.PIPELINE_COMPLETED.value == "PIPELINE_COMPLETED"
    assert MessageType.PIPELINE_ERROR.value == "PIPELINE_ERROR"
