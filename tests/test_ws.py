"""Tests for coordinator/ws.py and ws_handlers.py."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from agora.coordinator.models import MessageType, MotionStatus
from agora.coordinator.ws import ConnectionManager, manager
from agora.coordinator.ws_endpoint import on_agent_disconnect
from agora.coordinator.ws_handlers import handle_ping, handle_register, handle_speak
from agora.coordinator.ws_vote import handle_vote


@pytest.fixture
def mgr():
    return ConnectionManager()


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_agent = AsyncMock(return_value={"agent_id": "a1", "name": "Test"})
    s.set_agent_online = AsyncMock()
    s.add_message = AsyncMock(return_value=1)
    s.add_vote = AsyncMock(return_value=1)
    s.get_motion = AsyncMock(return_value={
        "id": "m1", "status": MotionStatus.DISCUSSING,
        "current_round": 1, "rounds": 3,
    })
    s.get_vote_summary = AsyncMock(return_value={"total_votes": 0})
    s.list_agents = AsyncMock(return_value=[{"agent_id": "a1"}])
    s.has_voted = AsyncMock(return_value=False)
    s.register_agent = AsyncMock(return_value={"agent_id": "a1"})
    return s


@pytest.fixture
def mock_sm():
    sm = AsyncMock()
    sm.can_speak = AsyncMock(return_value=True)
    sm.can_vote = AsyncMock(return_value=True)
    sm.transition = AsyncMock(return_value=MotionStatus.CLOSED)
    return sm


class TestConnectionManager:
    def test_init_empty(self, mgr):
        assert mgr.get_online_agents() == []

    @pytest.mark.asyncio
    async def test_connect_unregistered(self, mgr, mock_storage):
        ws = AsyncMock()
        mgr.set_deps(mock_storage, AsyncMock())
        mock_storage.get_agent = AsyncMock(return_value=None)
        result = await mgr.connect("a1", ws)
        assert result is False
        ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_registered(self, mgr, mock_storage):
        ws = AsyncMock()
        mgr.set_deps(mock_storage, AsyncMock())
        result = await mgr.connect("a1", ws)
        assert result is True
        assert "a1" in mgr.get_online_agents()

    @pytest.mark.asyncio
    async def test_disconnect(self, mgr, mock_storage):
        ws = AsyncMock()
        mgr.set_deps(mock_storage, AsyncMock())
        await mgr.connect("a1", ws)
        mgr.disconnect("a1")
        assert "a1" not in mgr.get_online_agents()

    @pytest.mark.asyncio
    async def test_send_to_connected(self, mgr, mock_storage):
        ws = AsyncMock()
        mgr.set_deps(mock_storage, AsyncMock())
        await mgr.connect("a1", ws)
        result = await mgr.send("a1", {"type": "PONG"})
        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_disconnected(self, mgr):
        result = await mgr.send("unknown", {"type": "PONG"})
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, mgr, mock_storage):
        ws1, ws2 = AsyncMock(), AsyncMock()
        mock_storage.get_agent = AsyncMock(
            side_effect=[{"agent_id": "a1"}, {"agent_id": "a2"}]
        )
        mgr.set_deps(mock_storage, AsyncMock())
        await mgr.connect("a1", ws1)
        await mgr.connect("a2", ws2)
        count = await mgr.broadcast({"type": "TEST"})
        assert count == 2

    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self, mgr, mock_storage):
        ws1, ws2 = AsyncMock(), AsyncMock()
        mock_storage.get_agent = AsyncMock(
            side_effect=[{"agent_id": "a1"}, {"agent_id": "a2"}]
        )
        mgr.set_deps(mock_storage, AsyncMock())
        await mgr.connect("a1", ws1)
        await mgr.connect("a2", ws2)
        count = await mgr.broadcast({"type": "TEST"}, exclude=["a2"])
        assert count == 1


class TestHandlers:
    @pytest.mark.asyncio
    async def test_handle_ping(self, mgr):
        mgr.send = AsyncMock(return_value=True)
        await handle_ping("a1", {}, mgr)
        mgr.send.assert_called_once()
        assert mgr.send.call_args[0][1]["type"] == MessageType.PONG

    @pytest.mark.asyncio
    async def test_handle_speak(self, mgr, mock_storage, mock_sm):
        mgr.send = AsyncMock(return_value=True)
        mgr.broadcast = AsyncMock(return_value=1)
        await handle_speak("a1", {
            "motion_id": "m1", "round": 1,
            "stance": "support", "content": "I agree",
        }, mock_storage, mock_sm, mgr)
        mock_storage.add_message.assert_called_once()
        mgr.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_speak_no_motion(self, mgr, mock_storage, mock_sm):
        mgr.send = AsyncMock(return_value=True)
        await handle_speak("a1", {}, mock_storage, mock_sm, mgr)
        assert mock_storage.add_message.call_count == 0

    @pytest.mark.asyncio
    async def test_handle_vote(self, mgr, mock_storage, mock_sm):
        mgr.send = AsyncMock(return_value=True)
        mgr.broadcast = AsyncMock(return_value=1)
        await handle_vote("a1", {
            "motion_id": "m1", "vote": "yes", "confidence": 0.9,
        }, mock_storage, mock_sm, mgr)
        mock_storage.add_vote.assert_called_once()
        mgr.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_vote_no_motion(self, mgr, mock_storage, mock_sm):
        mgr.send = AsyncMock(return_value=True)
        await handle_vote("a1", {}, mock_storage, mock_sm, mgr)
        assert mock_storage.add_vote.call_count == 0

    @pytest.mark.asyncio
    async def test_handle_register(self, mgr, mock_storage):
        mgr.send = AsyncMock(return_value=True)
        await handle_register("a1", {
            "name": "Test", "model": "gpt-4",
        }, mock_storage, mgr)
        mock_storage.register_agent.assert_called_once()
        mock_storage.set_agent_online.assert_called_once()


class TestOnDisconnect:
    @pytest.mark.asyncio
    async def test_marks_offline(self, mock_storage):
        with patch("agora.coordinator.ws_endpoint.manager") as m:
            m._storage = mock_storage
            m.broadcast = AsyncMock()
            await on_agent_disconnect("a1", m)
        mock_storage.set_agent_online.assert_called_with("a1", False)
