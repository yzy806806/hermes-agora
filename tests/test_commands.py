"""Tests for /agora slash command dispatch and help text.

Tests use direct import and mock tool calls at the module level.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, "/root/hermes-agora")


class TestHelpText:
    """Test /agora help and unknown subcommand output."""

    def test_help_returns_usage(self):
        from commands import _help_text
        result = _help_text()
        assert "/agora" in result
        assert "new" in result
        assert "list" in result
        assert "vote" in result
        assert "result" in result

    def test_help_contains_chinese(self):
        from commands import _help_text
        result = _help_text()
        assert "\u521b\u5efa" in result or "\u72b6\u6001" in result


class TestDispatch:
    """Test subcommand dispatch logic."""

    @pytest.mark.asyncio
    async def test_unknown_subcommand_returns_help(self):
        from commands import handle_agora
        result = await handle_agora("foobar")
        assert "/agora" in result

    @pytest.mark.asyncio
    async def test_help_subcommand(self):
        from commands import handle_agora
        result = await handle_agora("help")
        assert "/agora" in result

    @pytest.mark.asyncio
    async def test_question_mark_help(self):
        from commands import handle_agora
        result = await handle_agora("?")
        assert "/agora" in result
