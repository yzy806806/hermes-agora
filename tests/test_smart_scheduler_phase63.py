"""Tests for SmartDiscussionScheduler Phase 6.3 integration.

Tests realtime evaluation, consensus jump, and their integration
into the scheduler's decision flow.
"""
import pytest

from agora.coordinator.config import Settings
from agora.coordinator.models import MotionStatus
from agora.coordinator.smart_scheduler import SmartDiscussionScheduler
from agora.coordinator.state import StateMachine
from agora.coordinator.storage import Storage
from agora.coordinator.ws import ConnectionManager


def _make_config(**overrides) -> Settings:
    """Create a Settings with optional overrides."""
    return Settings(**overrides)


async def _seed_agents(storage: Storage, count: int) -> None:
    """Register agents for FK constraint."""
    for i in range(count):
        await storage.register_agent(f"a{i}", f"Agent{i}", "gpt-4")


@pytest.mark.asyncio
async def test_on_message_instant_consensus(storage: Storage):
    """on_message detects instant consensus and broadcasts."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    await _seed_agents(storage, 6)
    sm = StateMachine(storage)
    await sm.transition(mid, "start")
    ws = ConnectionManager()
    config = _make_config(
        realtime_consensus_threshold=0.8,
        realtime_min_messages=3,
    )
    scheduler = SmartDiscussionScheduler(storage, ws, sm, config)
    for i in range(4):
        await storage.add_message(mid, f"a{i}", 1, "support", "yes")
    msg = {"stance": "support", "agent_id": "a5", "content": "agree"}
    result = await scheduler.on_message(mid, msg)
    assert result is not None
    assert result.type == "INSTANT_CONSENSUS"


@pytest.mark.asyncio
async def test_on_message_disabled(storage: Storage):
    """on_message returns None when smart_discussion_enabled=False."""
    mid = (await storage.create_motion("T", "D", rounds=3))["id"]
    sm = StateMachine(storage)
    ws = ConnectionManager()
    config = _make_config(smart_discussion_enabled=False)
    scheduler = SmartDiscussionScheduler(storage, ws, sm, config)
    msg = {"stance": "support", "agent_id": "a1", "content": "ok"}
    result = await scheduler.on_message(mid, msg)
    assert result is None


@pytest.mark.asyncio
async def test_consensus_jump_all_agree(storage: Storage):
    """Consensus jump triggers voting when all agents agree."""
    mid = (await storage.create_motion("T", "D", rounds=5))["id"]
    await _seed_agents(storage, 4)
    sm = StateMachine(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    ws = ConnectionManager()
    config = _make_config(consensus_jump_ratio=0.7)
    scheduler = SmartDiscussionScheduler(storage, ws, sm, config)
    # All 4 support = 100% support -> only stance_support exists
    for i in range(4):
        await storage.add_message(mid, f"a{i}", 1, "support", "yes")
    await scheduler._continue_next_round(mid)
    motion = await storage.get_motion(mid)
    assert motion is not None
    assert motion["status"] == MotionStatus.VOTING.value


@pytest.mark.asyncio
async def test_no_jump_with_unresolved(storage: Storage):
    """No jump when there are unresolved sub-topics."""
    mid = (await storage.create_motion("T", "D", rounds=5))["id"]
    await _seed_agents(storage, 4)
    sm = StateMachine(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    ws = ConnectionManager()
    config = _make_config(consensus_jump_ratio=0.7)
    scheduler = SmartDiscussionScheduler(storage, ws, sm, config)
    # 2 support, 2 oppose = no consensus on either
    await storage.add_message(mid, "a0", 1, "support", "yes")
    await storage.add_message(mid, "a1", 1, "support", "yes")
    await storage.add_message(mid, "a2", 1, "oppose", "no")
    await storage.add_message(mid, "a3", 1, "oppose", "no")
    await scheduler._continue_next_round(mid)
    motion = await storage.get_motion(mid)
    assert motion is not None
    # Should NOT be voting — still discussing
    assert motion["status"] != MotionStatus.VOTING.value
