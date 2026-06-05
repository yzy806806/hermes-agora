"""Tests for Agent CRUD operations."""

import pytest

from coordinator.storage import Storage


@pytest.mark.asyncio
async def test_register_and_get_agent(storage: Storage):
    result = await storage.register_agent(
        "a1", "Agent One", "gpt-4", capabilities=["web_search"]
    )
    assert result["agent_id"] == "a1"

    agent = await storage.get_agent("a1")
    assert agent is not None
    assert agent["name"] == "Agent One"
    assert agent["model"] == "gpt-4"
    assert agent["is_online"] == 1


@pytest.mark.asyncio
async def test_get_agent_not_found(storage: Storage):
    assert await storage.get_agent("nonexistent") is None


@pytest.mark.asyncio
async def test_list_agents(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    await storage.set_agent_online("a2", False)

    all_agents = await storage.list_agents()
    assert len(all_agents) == 2

    online = await storage.list_agents(online_only=True)
    assert len(online) == 1
    assert online[0]["agent_id"] == "a1"


@pytest.mark.asyncio
async def test_set_agent_online(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.set_agent_online("a1", False)
    agent = await storage.get_agent("a1")
    assert agent["is_online"] == 0

    await storage.set_agent_online("a1", True)
    agent = await storage.get_agent("a1")
    assert agent["is_online"] == 1
    assert agent["last_seen_at"] is not None


@pytest.mark.asyncio
async def test_deregister_agent(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.deregister_agent("a1")
    assert await storage.get_agent("a1") is None
