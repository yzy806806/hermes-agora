"""Tests for storage/assessments.py CRUD operations."""

import pytest
import pytest_asyncio
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_assess.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest.mark.asyncio(loop_scope="session")
async def test_save_and_get_assessment(storage):
    """save_assessment + get_latest_assessment round-trip."""
    motion = await storage.create_motion("Test", "Desc")
    mid = motion["id"]
    aid = await storage.save_assessment(
        motion_id=mid, round_num=1,
        result="consensus_reached", consensus_level="high",
        metrics={"total_messages": 5, "quality": 0.8},
        rationale="Strong agreement",
    )
    assert aid > 0
    latest = await storage.get_latest_assessment(mid)
    assert latest is not None
    assert latest["motion_id"] == mid
    assert latest["result"] == "consensus_reached"
    assert latest["metrics"]["total_messages"] == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_get_latest_assessment_none(storage):
    """get_latest_assessment returns None for unknown motion."""
    result = await storage.get_latest_assessment("nonexistent")
    assert result is None


@pytest.mark.asyncio(loop_scope="session")
async def test_get_assessments_list(storage):
    """get_assessments returns all assessments for a motion."""
    motion = await storage.create_motion("Test2", "Desc")
    mid = motion["id"]
    await storage.save_assessment(
        mid, 1, "needs_more", "low",
        {"msg": 2}, "Not enough",
    )
    await storage.save_assessment(
        mid, 2, "sufficient", "medium",
        {"msg": 5}, "Better",
    )
    results = await storage.get_assessments(mid)
    assert len(results) == 2
    assert results[0]["round"] == 1
    assert results[1]["round"] == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_get_assessments_empty(storage):
    """get_assessments returns empty list for unknown motion."""
    results = await storage.get_assessments("no_such_motion")
    assert results == []
