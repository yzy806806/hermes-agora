"""Tests for /agora list subcommand."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHandleList:
    """Test /agora list subcommand."""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        from cmd_list import handle_list
        mock_list = AsyncMock(return_value={"motions": []})
        with patch("__init__.agora_list_motions", mock_list):
            result = await handle_list("")
        assert "\u65e0\u8bae\u9898" in result

    @pytest.mark.asyncio
    async def test_with_motions(self):
        from cmd_list import handle_list
        mock_list = AsyncMock(return_value={
            "motions": [
                {"id": "motion_1", "title": "Topic A", "status": "discussing"},
                {"id": "motion_2", "title": "Topic B", "status": "voting"},
            ]
        })
        with patch("__init__.agora_list_motions", mock_list):
            result = await handle_list("")
        assert "Topic A" in result
        assert "Topic B" in result

    @pytest.mark.asyncio
    async def test_status_filter(self):
        from cmd_list import handle_list
        mock_list = AsyncMock(return_value={"motions": []})
        with patch("__init__.agora_list_motions", mock_list):
            await handle_list("--status voting")
        mock_list.assert_called_once_with(
            status="voting", limit=10,
        )

    @pytest.mark.asyncio
    async def test_limit_option(self):
        from cmd_list import handle_list
        mock_list = AsyncMock(return_value={"motions": []})
        with patch("__init__.agora_list_motions", mock_list):
            await handle_list("--limit 5")
        mock_list.assert_called_once_with(status="discussing", limit=5)

    @pytest.mark.asyncio
    async def test_connection_error(self):
        from cmd_list import handle_list
        mock_list = AsyncMock(side_effect=ConnectionError("fail"))
        with patch("__init__.agora_list_motions", mock_list):
            result = await handle_list("")
        assert "\u274c" in result
