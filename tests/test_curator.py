"""Tests for coordinator/curator.py — DiscussionCurator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coordinator.curator import DiscussionCurator


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_motion = AsyncMock(return_value={
        "id": "m1", "title": "Test", "decision": "adopted",
    })
    s.get_votes = AsyncMock(return_value=[
        {"agent_id": "a1", "vote": "yes", "confidence": 0.9},
        {"agent_id": "a2", "vote": "no", "confidence": 0.7},
    ])
    return s


@pytest.fixture
def curator(mock_storage, tmp_path):
    db_path = str(tmp_path / "test.db")
    mem_path = str(tmp_path / "memories")
    return DiscussionCurator(mock_storage, db_path, mem_path)


class TestOptimizeMotion:
    @pytest.mark.asyncio
    async def test_returns_optimized_config(self, curator):
        motion = {"title": "架构升级", "rounds": 3}
        with patch.object(
            curator.history_pattern, "suggest_strategy",
            new_callable=AsyncMock,
            return_value={"strategy": "fast_track",
                          "suggested_rounds": 2,
                          "expected_consensus": "high",
                          "recommendations": ["提前投票"]},
        ), patch.object(
            curator.similar_detector, "generate_reference_context",
            new_callable=AsyncMock, return_value="",
        ):
            result = await curator.optimize_motion(motion)
        assert result["strategy"] == "fast_track"
        assert result["suggested_rounds"] == 2
        assert result["recommendations"] == ["提前投票"]

    @pytest.mark.asyncio
    async def test_low_consensus_adds_weighted_voters(self, curator):
        motion = {"title": "资源争议", "rounds": 5}
        mock_score = MagicMock()
        mock_score.agent_id = "expert_1"
        with patch.object(
            curator.history_pattern, "suggest_strategy",
            new_callable=AsyncMock,
            return_value={"strategy": "deep_discussion",
                          "suggested_rounds": 5,
                          "expected_consensus": "low",
                          "recommendations": []},
        ), patch.object(
            curator.similar_detector, "generate_reference_context",
            new_callable=AsyncMock, return_value="",
        ), patch.object(
            curator.judgment_tracker, "get_leaderboard",
            new_callable=AsyncMock,
            return_value=[mock_score],
        ):
            result = await curator.optimize_motion(motion)
        assert "weighted_voters" in result
        assert "expert_1" in result["weighted_voters"]


class TestPostDiscussionReview:
    @pytest.mark.asyncio
    async def test_records_votes(self, curator):
        with patch.object(
            curator.judgment_tracker, "record_vote",
            new_callable=AsyncMock,
        ) as mock_record:
            result = await curator.post_discussion_review("m1")
        assert result["motion_id"] == "m1"
        assert result["decision"] == "adopted"
        assert result["participants_evaluated"] == 2
        assert mock_record.call_count == 2

    @pytest.mark.asyncio
    async def test_motion_not_found(self, curator):
        curator.storage.get_motion = AsyncMock(return_value=None)
        result = await curator.post_discussion_review("missing")
        assert "error" in result
