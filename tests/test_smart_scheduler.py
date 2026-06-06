"""Tests for smart discussion state transitions and scheduler."""
import pytest

from coordinator.models import MotionStatus
from coordinator.state import StateMachine, InvalidTransitionError
from coordinator.storage import Storage


async def _make_motion(storage: Storage, rounds: int = 3) -> str:
    result = await storage.create_motion("Test", "Desc", rounds=rounds)
    return result["id"]


async def _make_agent(storage: Storage, agent_id: str = "a1") -> str:
    await storage.register_agent(agent_id, "Agent1", "gpt-4")
    return agent_id


# --- New state transition tests ---

@pytest.mark.asyncio
async def test_discussing_to_assessing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    new = await sm.transition(mid, "assess")
    assert new == MotionStatus.ASSESSING


@pytest.mark.asyncio
async def test_assessing_to_devils_advocate(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    new = await sm.transition(mid, "needs_devils_advocate")
    assert new == MotionStatus.DEVILS_ADVOCATE


@pytest.mark.asyncio
async def test_assessing_to_discussing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    new = await sm.transition(mid, "assessment_done")
    assert new == MotionStatus.DISCUSSING


@pytest.mark.asyncio
async def test_assessing_to_voting(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    new = await sm.transition(mid, "start_voting")
    assert new == MotionStatus.VOTING


@pytest.mark.asyncio
async def test_devils_advocate_to_discussing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    await sm.transition(mid, "needs_devils_advocate")
    new = await sm.transition(mid, "devils_advocate_done")
    assert new == MotionStatus.DISCUSSING


# --- Permission tests for new states ---

@pytest.mark.asyncio
async def test_can_speak_in_assessing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    assert await sm.can_speak(mid, aid) is True


@pytest.mark.asyncio
async def test_can_speak_in_devils_advocate(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "assess")
    await sm.transition(mid, "needs_devils_advocate")
    assert await sm.can_speak(mid, aid) is True


@pytest.mark.asyncio
async def test_invalid_transition_from_draft_assess(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    with pytest.raises(InvalidTransitionError):
        await sm.transition(mid, "assess")


@pytest.mark.asyncio
async def test_invalid_devils_advocate_from_discussing(
    storage: Storage,
):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    with pytest.raises(InvalidTransitionError):
        await sm.transition(mid, "needs_devils_advocate")
