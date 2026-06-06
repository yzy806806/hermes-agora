"""Tests for coordinator/focus.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from coordinator.focus import DisagreementFocus
from coordinator.models import Stance


def _make_storage(messages: list[dict]) -> MagicMock:
    """Create a mock Storage that returns the given messages."""
    storage = MagicMock()
    storage.get_messages = AsyncMock(return_value=messages)
    return storage


class TestIdentifyUnresolvedPoints:
    @pytest.mark.asyncio
    async def test_empty_messages(self):
        focus = DisagreementFocus(_make_storage([]))
        result = await focus.identify_unresolved_points("m1")
        assert result == []

    @pytest.mark.asyncio
    async def test_under_represented_oppose(self):
        msgs = [
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.OPPOSE},
        ]
        focus = DisagreementFocus(_make_storage(msgs))
        result = await focus.identify_unresolved_points("m1")
        assert any("oppose" in r for r in result)

    @pytest.mark.asyncio
    async def test_under_represented_neutral(self):
        msgs = [
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.OPPOSE},
            {"stance": Stance.OPPOSE},
        ]
        focus = DisagreementFocus(_make_storage(msgs))
        result = await focus.identify_unresolved_points("m1")
        assert any("neutral" in r for r in result)

    @pytest.mark.asyncio
    async def test_balanced_no_unresolved(self):
        msgs = [
            {"stance": Stance.SUPPORT},
            {"stance": Stance.OPPOSE},
            {"stance": Stance.NEUTRAL},
        ]
        focus = DisagreementFocus(_make_storage(msgs))
        result = await focus.identify_unresolved_points("m1")
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_stance_ignored(self):
        msgs = [{"stance": "unknown"}]
        focus = DisagreementFocus(_make_storage(msgs))
        result = await focus.identify_unresolved_points("m1")
        assert result == []


class TestGenerateFocusPrompt:
    @pytest.mark.asyncio
    async def test_no_unresolved(self):
        msgs = [
            {"stance": Stance.SUPPORT},
            {"stance": Stance.OPPOSE},
            {"stance": Stance.NEUTRAL},
        ]
        focus = DisagreementFocus(_make_storage(msgs))
        prompt = await focus.generate_focus_prompt("m1")
        assert "最终观点" in prompt

    @pytest.mark.asyncio
    async def test_with_unresolved(self):
        msgs = [
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
            {"stance": Stance.SUPPORT},
        ]
        focus = DisagreementFocus(_make_storage(msgs))
        prompt = await focus.generate_focus_prompt("m1")
        assert "分歧点" in prompt
        assert "oppose" in prompt
