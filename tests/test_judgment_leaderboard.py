"""Tests for judgment leaderboard and trend tracking."""

import pytest
import pytest_asyncio

from agora.coordinator.judgment_tracker import JudgmentTracker
from agora.coordinator.judgment_types import AgentScore
from agora.coordinator.storage.storage import Storage


@pytest_asyncio.fixture
async def judge_storage(tmp_path):
    """Storage with agents and a motion for FK constraints."""
    db_path = str(tmp_path / "judge_lb_test.db")
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


class TestJudgmentLeaderboard:
    """Tests for leaderboard and recent trend."""

    @pytest.mark.asyncio
    async def test_leaderboard_empty(self, tracker):
        board = await tracker.get_leaderboard()
        assert board == []

    @pytest.mark.asyncio
    async def test_leaderboard_ranking(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        await tracker.record_vote(mid, "agent_a", "adopted", "adopted", 0.9)
        await tracker.record_vote(mid, "agent_a", "rejected", "rejected", 0.8)
        await tracker.record_vote(mid, "agent_b", "adopted", "adopted", 0.9)
        await tracker.record_vote(mid, "agent_b", "rejected", "adopted", 0.7)
        board = await tracker.get_leaderboard()
        assert len(board) == 2
        assert board[0].agent_id == "agent_a"
        assert board[0].accuracy == 1.0
        assert board[1].agent_id == "agent_b"
        assert board[1].accuracy == 0.5

    @pytest.mark.asyncio
    async def test_recent_trend(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        await tracker.record_vote(mid, "agent_a", "adopted", "adopted", 0.9)
        await tracker.record_vote(mid, "agent_a", "rejected", "adopted", 0.7)
        score = await tracker.get_agent_score("agent_a")
        assert score.recent_trend == [0, 1]

    @pytest.mark.asyncio
    async def test_avg_confidence(self, tracker, judge_storage):
        mid = (await judge_storage.list_motions())[0]["id"]
        await tracker.record_vote(mid, "agent_a", "adopted", "adopted", 0.9)
        await tracker.record_vote(mid, "agent_a", "adopted", "adopted", 0.5)
        score = await tracker.get_agent_score("agent_a")
        assert score.avg_confidence == pytest.approx(0.7)
