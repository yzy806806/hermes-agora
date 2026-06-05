"""Tests for Message CRUD operations."""

import pytest

from coordinator.storage import Storage


@pytest.mark.asyncio
async def test_add_and_get_messages(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    m = await storage.create_motion("M", "D")
    mid = m["id"]

    msg_id = await storage.add_message(
        mid, "a1", 1, "support", "I agree",
        evidence=[{"type": "web_search", "query": "test"}],
    )
    assert msg_id > 0

    msgs = await storage.get_messages(mid)
    assert len(msgs) == 1
    assert msgs[0]["content"] == "I agree"
    assert msgs[0]["stance"] == "support"


@pytest.mark.asyncio
async def test_get_messages_filtered(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    await storage.register_agent("a2", "A2", "m2")
    m = await storage.create_motion("M", "D")
    mid = m["id"]

    await storage.add_message(mid, "a1", 1, "support", "R1 msg1")
    await storage.add_message(mid, "a2", 1, "oppose", "R1 msg2")
    await storage.add_message(mid, "a1", 2, "neutral", "R2 msg1")

    r1_msgs = await storage.get_messages(mid, round_num=1)
    assert len(r1_msgs) == 2

    a1_msgs = await storage.get_messages(mid, agent_id="a1")
    assert len(a1_msgs) == 2


@pytest.mark.asyncio
async def test_count_messages_by_round(storage: Storage):
    await storage.register_agent("a1", "A1", "m1")
    m = await storage.create_motion("M", "D")
    mid = m["id"]

    await storage.add_message(mid, "a1", 1, "support", "m1")
    await storage.add_message(mid, "a1", 1, "support", "m2")
    await storage.add_message(mid, "a1", 2, "neutral", "m3")

    assert await storage.count_messages_by_round(mid, 1) == 2
    assert await storage.count_messages_by_round(mid, 2) == 1
    assert await storage.count_messages_by_round(mid, 3) == 0
