"""Tests for /agora vote subcommand."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHandleVote:
    """Test /agora vote subcommand."""

    @pytest.mark.asyncio
    async def test_no_args_returns_usage(self):
        from cmd_vote import handle_vote
        result = await handle_vote("")
        assert "\u274c" in result

    @pytest.mark.asyncio
    async def test_missing_vote_choice(self):
        from cmd_vote import handle_vote
        result = await handle_vote("motion_1")
        assert "\u274c" in result

    @pytest.mark.asyncio
    async def test_invalid_vote_choice(self):
        from cmd_vote import handle_vote
        result = await handle_vote("motion_1 maybe")
        assert "\u274c" in result
        assert "yes" in result

    @pytest.mark.asyncio
    async def test_valid_yes_vote(self):
        from cmd_vote import handle_vote
        mock_vote = AsyncMock(
            return_value={"status": "voting", "total_votes": 2}
        )
        with patch("__init__.agora_vote", mock_vote):
            result = await handle_vote("motion_1 yes I agree")
        assert "yes" in result
        mock_vote.assert_called_once_with(
            motion_id="motion_1", vote="yes", reason="I agree",
        )

    @pytest.mark.asyncio
    async def test_valid_no_vote(self):
        from cmd_vote import handle_vote
        mock_vote = AsyncMock(
            return_value={"status": "voting", "total_votes": 1}
        )
        with patch("__init__.agora_vote", mock_vote):
            result = await handle_vote("motion_1 no")
        assert "no" in result

    @pytest.mark.asyncio
    async def test_valid_abstain_vote(self):
        from cmd_vote import handle_vote
        mock_vote = AsyncMock(
            return_value={"status": "voting", "total_votes": 3}
        )
        with patch("__init__.agora_vote", mock_vote):
            result = await handle_vote("motion_1 abstain")
        assert "abstain" in result

    @pytest.mark.asyncio
    async def test_vote_failure(self):
        from cmd_vote import handle_vote
        mock_vote = AsyncMock(side_effect=ConnectionError("fail"))
        with patch("__init__.agora_vote", mock_vote):
            result = await handle_vote("motion_1 yes")
        assert "\u274c" in result
