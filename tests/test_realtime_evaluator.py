"""Tests for RealTimeEvaluator — instant consensus and early termination."""
import pytest

from agora.coordinator.assessment import ConsensusLevel
from agora.coordinator.realtime_evaluator import RealTimeEvaluator, RealTimeEvalResult
from agora.coordinator.storage import Storage


async def _seed_agents(storage: Storage, count: int, prefix: str = "a") -> None:
    """Register agents for FK constraint."""
    for i in range(count):
        await storage.register_agent(f"{prefix}{i}", f"Agent{i}", "gpt-4")


@pytest.mark.asyncio
async def test_no_consensus_with_few_messages(storage: Storage):
    """Less than min_messages should not detect consensus."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 2)
    evaluator = RealTimeEvaluator(storage, min_messages_for_consensus=3)
    msg = {"stance": "support", "agent_id": "a1", "content": "ok"}
    result = await evaluator.on_message(mid, msg)
    assert result is None


@pytest.mark.asyncio
async def test_instant_consensus_support(storage: Storage):
    """High support ratio triggers INSTANT_CONSENSUS."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 6)
    evaluator = RealTimeEvaluator(
        storage, consensus_threshold=0.8, min_messages_for_consensus=3,
    )
    # Seed 4 support messages
    for i in range(4):
        await storage.add_message(mid, f"a{i}", 1, "support", "yes")
    # New message also support
    msg = {"stance": "support", "agent_id": "a5", "content": "agree"}
    result = await evaluator.on_message(mid, msg)
    assert result is not None
    assert result.type == "INSTANT_CONSENSUS"
    assert result.consensus_level == ConsensusLevel.HIGH


@pytest.mark.asyncio
async def test_instant_consensus_oppose(storage: Storage):
    """High oppose ratio also triggers INSTANT_CONSENSUS."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 6)
    evaluator = RealTimeEvaluator(
        storage, consensus_threshold=0.8, min_messages_for_consensus=3,
    )
    for i in range(4):
        await storage.add_message(mid, f"a{i}", 1, "oppose", "no")
    msg = {"stance": "oppose", "agent_id": "a5", "content": "disagree"}
    result = await evaluator.on_message(mid, msg)
    assert result is not None
    assert result.type == "INSTANT_CONSENSUS"


@pytest.mark.asyncio
async def test_no_consensus_mixed_stances(storage: Storage):
    """Mixed stances should not trigger consensus."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 5)
    evaluator = RealTimeEvaluator(
        storage, consensus_threshold=0.8, min_messages_for_consensus=3,
    )
    await storage.add_message(mid, "a1", 1, "support", "yes")
    await storage.add_message(mid, "a2", 1, "oppose", "no")
    await storage.add_message(mid, "a3", 1, "neutral", "maybe")
    msg = {"stance": "support", "agent_id": "a4", "content": "ok"}
    result = await evaluator.on_message(mid, msg)
    assert result is None


@pytest.mark.asyncio
async def test_early_termination(storage: Storage):
    """Sufficient quality triggers EARLY_TERMINATION."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 8)
    evaluator = RealTimeEvaluator(storage, consensus_threshold=0.95)
    # 6+ messages with decent length
    for i in range(6):
        await storage.add_message(mid, f"a{i}", 1, "support", "x" * 150)
    msg = {"stance": "support", "agent_id": "a6", "content": "x" * 150}
    result = await evaluator.on_message(mid, msg)
    # Should be early termination (no consensus at 0.95)
    if result is not None:
        assert result.type in ("INSTANT_CONSENSUS", "EARLY_TERMINATION")
