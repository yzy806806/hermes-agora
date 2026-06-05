"""Tests for /agora status subcommand."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHandleStatus:
    """Test /agora status subcommand."""

    @pytest.mark.asyncio
    async def test_no_args_returns_usage(self):
        from cmd_status import handle_status
        result = await handle_status("")
        assert "\u274c" in result

    @pytest.mark.asyncio
    async def test_shows_motion_detail(self):
        from cmd_status import handle_status
        mock_hist = AsyncMock(return_value={
            "title": "Test Motion",
            "status": "discussing",
            "current_round": 1,
            "total_rounds": 3,
            "participants": [{"name": "Alpha"}],
            "speeches": [],
        })
        with patch("__init__.agora_get_history", mock_hist):
            result = await handle_status("motion_abc")
        assert "Test Motion" in result
        assert "motion_abc" in result
        assert "Alpha" in result

    @pytest.mark.asyncio
    async def test_voting_status_shows_vote_hint(self):
        from cmd_status import handle_status
        mock_hist = AsyncMock(return_value={
            "title": "Vote Topic",
            "status": "voting",
            "current_round": 3,
            "total_rounds": 3,
            "participants": [],
            "speeches": [],
        })
        with patch("__init__.agora_get_history", mock_hist):
            result = await handle_status("motion_v1")
        assert "/agora vote" in result

    @pytest.mark.asyncio
    async def test_with_speeches(self):
        from cmd_status import handle_status
        mock_hist = AsyncMock(return_value={
            "title": "Talk",
            "status": "discussing",
            "participants": [],
            "speeches": [
                {"agent_id": "A", "stance": "pro", "content": "I agree"},
            ],
        })
        with patch("__init__.agora_get_history", mock_hist):
            result = await handle_status("motion_s1")
        assert "I agree" in result
