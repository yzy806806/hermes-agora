"""Tests for ConsensusJumpManager — sub-topic consensus analysis."""
import pytest

from agora.coordinator.consensus_jump import ConsensusJumpManager, SubTopicConsensus
from agora.coordinator.storage import Storage


async def _seed_agents(storage: Storage, count: int) -> None:
    """Register agents for FK constraint."""
    for i in range(count):
        await storage.register_agent(f"a{i}", f"Agent{i}", "gpt-4")


@pytest.mark.asyncio
async def test_analyze_empty_motion(storage: Storage):
    """No messages returns empty list."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    mgr = ConsensusJumpManager(storage)
    result = await mgr.analyze_sub_topics(mid)
    assert result == []


@pytest.mark.asyncio
async def test_analyze_consensus_reached(storage: Storage):
    """Majority stance triggers consensus."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 4)
    mgr = ConsensusJumpManager(storage, consensus_ratio=0.7)
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await storage.add_message(mid, "a1", 1, "support", "yes")
    await storage.add_message(mid, "a2", 1, "support", "yes")
    await storage.add_message(mid, "a3", 1, "oppose", "no")
    result = await mgr.analyze_sub_topics(mid)
    support_topic = [r for r in result if r.topic == "stance_support"]
    assert len(support_topic) == 1
    assert support_topic[0].consensus_reached is True


@pytest.mark.asyncio
async def test_analyze_no_consensus(storage: Storage):
    """Even split means no consensus."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 2)
    mgr = ConsensusJumpManager(storage, consensus_ratio=0.7)
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await storage.add_message(mid, "a1", 1, "oppose", "no")
    result = await mgr.analyze_sub_topics(mid)
    for r in result:
        assert r.consensus_reached is False


@pytest.mark.asyncio
async def test_get_focus_topics(storage: Storage):
    """Only non-consensus topics are focus topics."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 4)
    mgr = ConsensusJumpManager(storage, consensus_ratio=0.7)
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await storage.add_message(mid, "a1", 1, "support", "yes")
    await storage.add_message(mid, "a2", 1, "support", "yes")
    await storage.add_message(mid, "a3", 1, "oppose", "no")
    focus = await mgr.get_focus_topics(mid)
    assert "stance_support" not in focus


@pytest.mark.asyncio
async def test_get_consensus_topics(storage: Storage):
    """Returns only topics where consensus is reached."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 4)
    mgr = ConsensusJumpManager(storage, consensus_ratio=0.7)
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await storage.add_message(mid, "a1", 1, "support", "yes")
    await storage.add_message(mid, "a2", 1, "support", "yes")
    await storage.add_message(mid, "a3", 1, "oppose", "no")
    agreed = await mgr.get_consensus_topics(mid)
    assert "stance_support" in agreed


@pytest.mark.asyncio
async def test_clear_cache(storage: Storage):
    """Cache can be cleared per motion or entirely."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 1)
    mgr = ConsensusJumpManager(storage)
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await mgr.analyze_sub_topics(mid)
    assert mid in mgr._consensus_cache
    mgr.clear_cache(mid)
    assert mid not in mgr._consensus_cache
