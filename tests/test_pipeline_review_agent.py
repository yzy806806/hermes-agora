"""Tests for pipeline_review_agent: find_review_agent,
await_online_agents, get_agent_capabilities."""
import pytest
from unittest.mock import MagicMock

from agora.coordinator.pipeline_review_agent import (
    await_online_agents, find_review_agent, get_agent_capabilities,
)


def _make_hub_with_registry(agents, registry):
    hub = MagicMock()
    hub.get_online_agents.return_value = agents
    hub._app_state = MagicMock()
    hub._app_state.agent_registry = registry
    return hub


@pytest.mark.asyncio
async def test_await_online_agents_sync():
    """Sync list returned directly."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["a", "b"]
    result = await await_online_agents(hub)
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_find_review_agent_capability():
    """Finds agent with code-review capability."""
    hub = _make_hub_with_registry(
        ["dev-1", "reviewer-1"],
        {"dev-1": {"capabilities": ["code"]},
         "reviewer-1": {"capabilities": ["code-review"]}},
    )
    assert await find_review_agent(hub) == "reviewer-1"


@pytest.mark.asyncio
async def test_find_review_agent_name_fallback():
    """Falls back to name-based heuristic."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["dev-1", "code-reviewer"]
    hub._app_state = None
    assert await find_review_agent(hub) == "code-reviewer"


@pytest.mark.asyncio
async def test_find_review_agent_none():
    """Returns None when no review agent available."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["dev-1"]
    hub._app_state = None
    assert await find_review_agent(hub) is None


def test_get_agent_capabilities_with_registry():
    """Extracts capabilities from agent registry."""
    hub = MagicMock()
    hub._app_state = MagicMock()
    hub._app_state.agent_registry = {
        "r1": {"capabilities": ["code-review"]},
    }
    assert get_agent_capabilities(hub, "r1") == ["code-review"]


def test_get_agent_capabilities_no_state():
    """Returns empty list when no app_state."""
    hub = MagicMock(spec=[])
    assert get_agent_capabilities(hub, "r1") == []
