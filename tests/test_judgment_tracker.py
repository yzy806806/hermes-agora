"""Tests for coordinator/judgment_tracker.py and storage/judgments.py."""

import pytest
import pytest_asyncio

from coordinator.judgment_tracker import JudgmentTracker
from coordinator.judgment_types import AgentScore
from coordinator.storage.storage import Storage


@pytest_asyncio.fixture
async def judge_storage(tmp_path):
    """Storage with agents and a motion for FK constraints."""
    db_path = str(tmp_path / "judge_test.db")
    s = Storage(db_path)
    await s.init_db()
    await s.register_agent("agent_a", "Agent A", "gpt-4")
    await s.register_agent("agent_b", "Agent B", "claude-3")
    await s.register_agent("agent_c", "Agent C", "llama-3")
    await s.create_motion("Test Motion", "Test Description")
    yield s


@pytest.fixture
def tracker(judge_storage):
    """Create a JudgmentTracker from storage."""
    return JudgmentTracker(judge_storage)


class TestJudgmentTracker:
    """Tests for JudgmentTracker class."""

    @pytest.mark.asyncio
    async def test_record_vote_correct(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        rid = await tracker.record_vote(
            mid, "agent_a", "adopted", "adopted", 0.9)
        assert rid > 0

    @pytest.mark.asyncio
    async def test_record_vote_incorrect(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        await tracker.record_vote(
            mid, "agent_a", "adopted", "rejected", 0.8)

    @pytest.mark.asyncio
    async def test_get_agent_score_new(self, tracker):
        score = await tracker.get_agent_score("agent_a")
        assert isinstance(score, AgentScore)
        assert score.agent_id == "agent_a"
        assert score.total_decisions == 0
        assert score.accuracy == 0.0
