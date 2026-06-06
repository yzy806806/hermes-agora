"""Tests for AdvancedVotingManager."""

import pytest
from unittest.mock import AsyncMock, patch

from coordinator.voting.manager import AdvancedVotingManager
from coordinator.models import MotionStatus, VotingMethod


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.get_motion.return_value = {
        "id": "m1",
        "status": MotionStatus.VOTING,
        "voting_method": VotingMethod.SIMPLE_MAJORITY,
    }
    storage.get_votes.return_value = [
        {"agent_id": "a1", "vote": "yes", "confidence": 1.0},
        {"agent_id": "a2", "vote": "no", "confidence": 1.0},
        {"agent_id": "a3", "vote": "yes", "confidence": 1.0},
    ]
    return storage


@pytest.fixture
def mock_ws():
    return AsyncMock()


@pytest.fixture
def manager(mock_storage, mock_ws):
    return AdvancedVotingManager(mock_storage, mock_ws, {})


class TestHandleVote:
    """handle_vote validation and storage."""

    @pytest.mark.asyncio
    async def test_valid_binary_vote(self, manager, mock_storage):
        vote_data = {"type": "binary", "vote": "yes", "confidence": 0.9}
        await manager.handle_vote("a1", "m1", vote_data)
        mock_storage.add_vote.assert_called_once()
        call_kwargs = mock_storage.add_vote.call_args
        assert call_kwargs[1]["vote_type"] == "binary"

    @pytest.mark.asyncio
    async def test_invalid_state(self, manager, mock_storage, mock_ws):
        mock_storage.get_motion.return_value = {
            "status": MotionStatus.DRAFT,
            "voting_method": "simple_majority",
        }
        await manager.handle_vote("a1", "m1", {"vote": "yes"})
        mock_ws.send.assert_called_once()
        msg = mock_ws.send.call_args[0][1]
        assert msg["payload"]["code"] == "INVALID_STATE"

    @pytest.mark.asyncio
    async def test_invalid_format(self, manager, mock_storage, mock_ws):
        # ranking data on binary method
        await manager.handle_vote("a1", "m1", {
            "type": "ranking", "ranking": ["A", "B"]
        })
        mock_ws.send.assert_called_once()
        msg = mock_ws.send.call_args[0][1]
        assert msg["payload"]["code"] == "INVALID_VOTE_FORMAT"


class TestValidateVoteFormat:
    """_validate_vote_format logic."""

    def test_binary_method_binary_data(self, manager):
        assert manager._validate_vote_format("simple_majority", {
            "type": "binary", "vote": "yes"
        })

    def test_binary_method_ranking_data(self, manager):
        assert not manager._validate_vote_format("simple_majority", {
            "type": "ranking", "ranking": ["A"]
        })

    def test_ranked_choice_method(self, manager):
        assert manager._validate_vote_format("ranked_choice", {
            "type": "ranking", "ranking": ["A", "B"]
        })

    def test_borda_count_method(self, manager):
        assert manager._validate_vote_format("borda_count", {
            "type": "ranking", "ranking": ["A", "B"]
        })

    def test_unknown_method_passes(self, manager):
        assert manager._validate_vote_format("custom", {"vote": "yes"})


class TestCloseVoting:
    """close_voting counting and broadcast."""

    @pytest.mark.asyncio
    async def test_simple_majority_close(self, manager, mock_ws):
        result = await manager.close_voting("m1")
        assert result["decision"] == "adopted"
        mock_ws.broadcast.assert_called_once()
        payload = mock_ws.broadcast.call_args[0][0]
        assert payload["type"] == "RESULT"

    @pytest.mark.asyncio
    async def test_motion_not_found(self, manager, mock_storage):
        mock_storage.get_motion.return_value = None
        with pytest.raises(ValueError):
            await manager.close_voting("missing")

    @pytest.mark.asyncio
    async def test_weighted_close(self, mock_storage, mock_ws):
        mock_storage.get_motion.return_value = {
            "id": "m1",
            "status": MotionStatus.VOTING,
            "voting_method": VotingMethod.WEIGHTED,
        }
        mock_storage.list_agents.return_value = [
            {"agent_id": "a1"}, {"agent_id": "a2"},
        ]
        mgr = AdvancedVotingManager(
            mock_storage, mock_ws,
            {"weight_strategy": "manual", "manual_weights": {"a1": 2.0}},
        )
        result = await mgr.close_voting("m1")
        # a1=yes(2.0), a2=no(1.0) -> ratio=2/3 -> adopted
        assert result["decision"] == "adopted"
