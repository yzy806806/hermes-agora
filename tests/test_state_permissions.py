"""Tests for can_speak and can_vote permission checks."""

import pytest

from coordinator.models import MotionStatus
from coordinator.state import StateMachine
from coordinator.storage import Storage


async def _make_motion(storage: Storage, rounds: int = 3) -> str:
    result = await storage.create_motion("Test", "Desc", rounds=rounds)
    return result["id"]


async def _make_agent(storage: Storage, agent_id: str = "a1") -> str:
    await storage.register_agent(agent_id, "Agent1", "gpt-4")
    return agent_id


# --- can_speak tests ---

@pytest.mark.asyncio
async def test_can_speak_in_discussing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage)
    await sm.transition(mid, "start")
    assert await sm.can_speak(mid, aid) is True


@pytest.mark.asyncio
async def test_cannot_speak_in_draft(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage)
    assert await sm.can_speak(mid, aid) is False


@pytest.mark.asyncio
async def test_cannot_speak_unregistered_agent(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    assert await sm.can_speak(mid, "unknown") is False


@pytest.mark.asyncio
async def test_cannot_speak_nonexistent_motion(storage: Storage):
    sm = StateMachine(storage)
    assert await sm.can_speak("nonexistent", "a1") is False


# --- can_vote tests ---

@pytest.mark.asyncio
async def test_can_vote_in_voting(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage, "voter1")
    await sm.transition(mid, "start")
    await sm.transition(mid, "start_voting")
    assert await sm.can_vote(mid, aid) is True


@pytest.mark.asyncio
async def test_cannot_vote_in_discussing(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage, "voter2")
    await sm.transition(mid, "start")
    assert await sm.can_vote(mid, aid) is False


@pytest.mark.asyncio
async def test_cannot_vote_twice(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    aid = await _make_agent(storage, "voter3")
    await sm.transition(mid, "start")
    await sm.transition(mid, "start_voting")
    await storage.add_vote(mid, aid, "yes", 1.0)
    assert await sm.can_vote(mid, aid) is False


@pytest.mark.asyncio
async def test_cannot_vote_unregistered(storage: Storage):
    sm = StateMachine(storage)
    mid = await _make_motion(storage)
    await sm.transition(mid, "start")
    await sm.transition(mid, "start_voting")
    assert await sm.can_vote(mid, "unknown") is False
