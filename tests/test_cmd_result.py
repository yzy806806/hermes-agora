"""Tests for /agora result subcommand."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHandleResult:
    """Test /agora result subcommand."""

    @pytest.mark.asyncio
    async def test_no_args_returns_usage(self):
        from cmd_result import handle_result
        result = await handle_result("")
        assert "\u274c" in result

    @pytest.mark.asyncio
    async def test_passed_result(self):
        from cmd_result import handle_result
        mock_result = AsyncMock(return_value={
            "title": "Test Motion",
            "status": "closed",
            "decision": "passed",
            "votes": {"yes": 2, "no": 1, "abstain": 0},
            "rationale": "Majority supports",
        })
        with patch("__init__.agora_get_result", mock_result):
            result = await handle_result("motion_1")
        assert "Test Motion" in result
        assert "\u901a\u8fc7" in result
        assert "66.7%" in result

    @pytest.mark.asyncio
    async def test_rejected_result(self):
        from cmd_result import handle_result
        mock_result = AsyncMock(return_value={
            "title": "Bad Idea",
            "status": "closed",
            "decision": "rejected",
            "votes": {"yes": 1, "no": 2, "abstain": 0},
        })
        with patch("__init__.agora_get_result", mock_result):
            result = await handle_result("motion_2")
        assert "\u5426\u51b3" in result

    @pytest.mark.asyncio
    async def test_no_votes(self):
        from cmd_result import handle_result
        mock_result = AsyncMock(return_value={
            "title": "Empty",
            "status": "closed",
            "decision": "pending",
            "votes": {},
        })
        with patch("__init__.agora_get_result", mock_result):
            result = await handle_result("motion_3")
        assert "\u65e0\u6295\u7968\u6570\u636e" in result

    @pytest.mark.asyncio
    async def test_connection_error(self):
        from cmd_result import handle_result
        mock_result = AsyncMock(side_effect=ConnectionError("fail"))
        with patch("__init__.agora_get_result", mock_result):
            result = await handle_result("motion_1")
        assert "\u274c" in result
