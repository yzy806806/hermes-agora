"""Tests for release agent lookup and trigger (Phase 13.1d)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agora.coordinator.pipeline_release_agent import find_release_agent
from agora.coordinator.pipeline_phase_release import (
    trigger_release, process_release_result,
)
from agora.coordinator.pipeline_release_models import ReleaseResult
from agora.coordinator.pipeline_errors import ReleaseFailedError


def _hub_with_agents(*agent_ids: str) -> MagicMock:
    hub = MagicMock()
    hub.get_online_agents.return_value = list(agent_ids)
    hub.send = AsyncMock(return_value=True)
    hub._app_state = MagicMock()
    hub._app_state.agent_registry = {}
    return hub


def _hub_with_caps(agent_id: str, caps: list[str]) -> MagicMock:
    hub = _hub_with_agents(agent_id)
    hub._app_state.agent_registry[agent_id] = {"capabilities": caps}
    return hub


class TestFindReleaseAgent:
    @pytest.mark.asyncio
    async def test_capability_match(self):
        hub = _hub_with_caps("agent-1", ["release"])
        assert await find_release_agent(hub) == "agent-1"

    @pytest.mark.asyncio
    async def test_name_fallback(self):
        hub = _hub_with_agents("releaser-bot")
        assert await find_release_agent(hub) == "releaser-bot"

    @pytest.mark.asyncio
    async def test_no_agent(self):
        hub = _hub_with_agents("worker-1")
        assert await find_release_agent(hub) is None
