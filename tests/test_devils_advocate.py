"""Tests for coordinator/devils_advocate.py."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coordinator.devils_advocate import (
    DevilsAdvocateConfig,
    DevilsAdvocateManager,
)
from coordinator.models import Stance


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_messages = AsyncMock(return_value=[])
    s.get_motion = AsyncMock(return_value={
        "id": "m1",
        "title": "Test Motion",
        "description": "A test",
        "current_round": 1,
    })
    s.list_agents = AsyncMock(return_value=[
        {"agent_id": "a1"},
        {"agent_id": "a2"},
        {"agent_id": "a3"},
    ])
    return s


@pytest.fixture
def mock_ws():
    return AsyncMock()


class TestDevilsAdvocateConfig:
    def test_defaults(self):
        c = DevilsAdvocateConfig()
        assert c.enabled is True
        assert c.trigger_threshold == 0.7
        assert c.max_triggers_per_motion == 2


class TestDevilsAdvocateManager:
    @pytest.mark.asyncio
    async def test_disabled_returns_false(self, mock_storage, mock_ws):
        cfg = DevilsAdvocateConfig(enabled=False)
        mgr = DevilsAdvocateManager(mock_storage, mock_ws, cfg)
        should, agent = await mgr.should_trigger("m1")
        assert should is False
        assert agent is None

    @pytest.mark.asyncio
    async def test_too_few_messages(self, mock_storage, mock_ws):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": Stance.SUPPORT},
        ])
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        should, agent = await mgr.should_trigger("m1")
        assert should is False

    @pytest.mark.asyncio
    async def test_max_triggers_reached(self, mock_storage, mock_ws):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": Stance.SUPPORT},
            {"agent_id": "a2", "stance": Stance.SUPPORT},
            {"agent_id": "a3", "stance": Stance.SUPPORT},
        ])
        cfg = DevilsAdvocateConfig(max_triggers_per_motion=2)
        mgr = DevilsAdvocateManager(mock_storage, mock_ws, cfg)
        mgr._trigger_count["m1"] = 2
        should, agent = await mgr.should_trigger("m1")
        assert should is False

    @pytest.mark.asyncio
    async def test_support_below_threshold(self, mock_storage, mock_ws):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": Stance.SUPPORT},
            {"agent_id": "a2", "stance": Stance.OPPOSE},
            {"agent_id": "a3", "stance": Stance.NEUTRAL},
        ])
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        should, agent = await mgr.should_trigger("m1")
        assert should is False

    @pytest.mark.asyncio
    async def test_triggers_when_support_high(self, mock_storage, mock_ws):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": Stance.SUPPORT},
            {"agent_id": "a2", "stance": Stance.SUPPORT},
            {"agent_id": "a3", "stance": Stance.SUPPORT},
        ])
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        should, agent = await mgr.should_trigger("m1")
        assert should is True
        assert agent in {"a1", "a2", "a3"}

    @pytest.mark.asyncio
    async def test_excludes_already_opposed(self, mock_storage, mock_ws):
        # 3 support, 1 oppose = 75% support, above threshold
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": Stance.SUPPORT},
            {"agent_id": "a2", "stance": Stance.SUPPORT},
            {"agent_id": "a3", "stance": Stance.SUPPORT},
            {"agent_id": "a4", "stance": Stance.OPPOSE},
        ])
        mock_storage.list_agents = AsyncMock(return_value=[
            {"agent_id": "a1"},
            {"agent_id": "a2"},
            {"agent_id": "a3"},
            {"agent_id": "a4"},
        ])
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        should, agent = await mgr.should_trigger("m1")
        assert should is True
        # a4 already opposed, so should pick from a1, a2, a3
        assert agent in {"a1", "a2", "a3"}

    @pytest.mark.asyncio
    async def test_trigger_sends_message(self, mock_storage, mock_ws):
        mock_ws.send = AsyncMock(return_value=True)
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        await mgr.trigger("m1", "a1")
        mock_ws.send.assert_called_once()
        msg = mock_ws.send.call_args[0][1]
        assert msg["type"] == "DEVILS_ADVOCATE_REQUEST"
        assert msg["motion_id"] == "m1"
        assert "instruction" in msg["payload"]

    @pytest.mark.asyncio
    async def test_trigger_increments_count(self, mock_storage, mock_ws):
        mock_ws.send = AsyncMock(return_value=True)
        mgr = DevilsAdvocateManager(mock_storage, mock_ws)
        assert mgr._trigger_count.get("m1", 0) == 0
        await mgr.trigger("m1", "a1")
        assert mgr._trigger_count["m1"] == 1
        await mgr.trigger("m1", "a2")
        assert mgr._trigger_count["m1"] == 2
