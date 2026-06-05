"""Tests for Vote CRUD and statistics operations."""

import pytest

from coordinator.storage import Storage


@pytest.mark.asyncio
async def test_add_and_get_votes(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    motion = await storage.create_motion("M", "D")
    mid = motion["id"]

    v1 = await storage.add_vote(mid, "a1", "yes", 0.9, "Looks good")
    v2 = await storage.add_vote(mid, "a2", "no", 0.7, "Needs work")
    assert v1 > 0 and v2 > 0

    votes = await storage.get_votes(mid)
    assert len(votes) == 2


@pytest.mark.asyncio
async def test_has_voted(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    motion = await storage.create_motion("M", "D")
    mid = motion["id"]

    assert await storage.has_voted(mid, "a1") is False
    await storage.add_vote(mid, "a1", "yes")
    assert await storage.has_voted(mid, "a1") is True


@pytest.mark.asyncio
async def test_count_votes(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    await storage.register_agent("a3", "A3", "m3")
    motion = await storage.create_motion("M", "D")
    mid = motion["id"]

    await storage.add_vote(mid, "a1", "yes")
    await storage.add_vote(mid, "a2", "yes")
    await storage.add_vote(mid, "a3", "no")

    counts = await storage.count_votes(mid)
    assert counts == {"yes": 2, "no": 1}


@pytest.mark.asyncio
async def test_get_vote_summary(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    motion = await storage.create_motion("M", "D")
    mid = motion["id"]

    await storage.add_vote(mid, "a1", "yes")
    await storage.add_vote(mid, "a2", "abstain")

    summary = await storage.get_vote_summary(mid)
    assert summary["yes"] == 1
    assert summary["abstain"] == 1
    assert summary["total"] == 2


@pytest.mark.asyncio
async def test_statistics(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    await storage.create_motion("M1", "D1")
    m2 = await storage.create_motion("M2", "D2")
    await storage.update_motion_status(m2["id"], "closed")

    assert await storage.get_active_motion_count() == 1
    assert await storage.get_participant_count() == 2
