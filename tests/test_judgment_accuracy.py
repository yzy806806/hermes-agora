"""Tests for judgment accuracy calculation and weighted voting."""

import pytest
import pytest_asyncio

from agora.coordinator.judgment_tracker import JudgmentTracker
from agora.coordinator.judgment_types import AgentScore
from agora.coordinator.storage.storage import Storage


@pytest_asyncio.fixture
async def judge_storage(tmp_path):
    """Storage with agents and a motion for FK constraints."""
    db_path = str(tmp_path / "judge_acc_test.db")
    s = Storage(db_path)
    await s.init_db()
    await s.register_agent("agent_a", "Agent A", "gpt-4")
    await s.register_agent("agent_b", "Agent B", "claude-3")
    await s.register_agent("agent_c", "Agent C", "llama-3")
    await s.create_motion("Test Motion", "Test Description")
    yield s


@pytest.fixture
def tracker(judge_storage):
    return JudgmentTracker(judge_storage)


class TestJudgmentTrackerAccuracy:
    """Tests for accuracy calculation and weighted voting."""

    @pytest.mark.asyncio
    async def test_accuracy_after_votes(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        await tracker.record_vote(mid, "agent_a", "adopted", "adopted", 0.9)
        await tracker.record_vote(mid, "agent_a", "rejected", "adopted", 0.7)
        score = await tracker.get_agent_score("agent_a")
        assert score.total_decisions == 2
        assert score.correct_predictions == 1
        assert score.accuracy == 0.5

    @pytest.mark.asyncio
    async def test_weighted_vote_new_agent(self, tracker):
        weight = await tracker.get_weighted_vote("agent_b")
        assert weight == 1.0

    @pytest.mark.asyncio
    async def test_weighted_vote_experienced(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        for _ in range(3):
            await tracker.record_vote(
                mid, "agent_b", "adopted", "adopted", 0.9)
        weight = await tracker.get_weighted_vote("agent_b")
        assert weight == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_weighted_vote_low_accuracy(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        for _ in range(3):
            await tracker.record_vote(
                mid, "agent_c", "adopted", "rejected", 0.5)
        weight = await tracker.get_weighted_vote("agent_c")
        assert weight == pytest.approx(0.5)
