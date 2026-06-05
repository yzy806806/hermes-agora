"""Tests for /agora new subcommand."""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHandleNew:
    """Test /agora new subcommand."""

    @pytest.mark.asyncio
    async def test_no_args_returns_usage(self):
        from cmd_new import handle_new
        result = await handle_new("")
        assert "\u274c" in result
        assert "\u7528\u6cd5" in result

    @pytest.mark.asyncio
    async def test_creates_motion(self):
        from cmd_new import handle_new
        mock_create = AsyncMock(
            return_value={"id": "motion_test1", "status": "draft"}
        )
        with patch("__init__.agora_create_motion", mock_create):
            result = await handle_new("TestTopic")
        assert "motion_test1" in result
        assert "TestTopic" in result

    @pytest.mark.asyncio
    async def test_invalid_rounds(self):
        from cmd_new import handle_new
        result = await handle_new("Test -r abc")
        assert "\u274c" in result

    @pytest.mark.asyncio
    async def test_with_options(self):
        from cmd_new import handle_new
        mock_create = AsyncMock(
            return_value={"id": "motion_opt", "status": "draft"}
        )
        with patch("__init__.agora_create_motion", mock_create):
            result = await handle_new(
                "Topic -d desc -r 2 -v supermajority"
            )
        mock_create.assert_called_once_with(
            title="Topic", description="desc",
            rounds=2, voting_method="supermajority",
        )

    @pytest.mark.asyncio
    async def test_create_failure(self):
        from cmd_new import handle_new
        mock_create = AsyncMock(side_effect=ConnectionError("fail"))
        with patch("__init__.agora_create_motion", mock_create):
            result = await handle_new("Topic")
        assert "\u274c" in result
