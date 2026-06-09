"""Tests for coordinator/heartbeat.py."""
import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.heartbeat import HeartbeatManager, AgentConnectionStatus


@pytest.fixture
def mgr():
    """Create a mock ConnectionManager."""
    m = MagicMock()
    m.active_connections = {}
    m.send = AsyncMock(return_value=True)
    return m


@pytest.fixture
def hb(mgr):
    """Create a HeartbeatManager with mock ConnectionManager."""
    return HeartbeatManager(mgr)


class TestAgentConnectionStatus:
    def test_enum_values(self):
        assert AgentConnectionStatus.ACTIVE == "active"
        assert AgentConnectionStatus.UNRESPONSIVE == "unresponsive"
        assert AgentConnectionStatus.OFFLINE == "offline"


class TestHandlePong:
    def test_clears_pending_ping(self, hb):
        hb.pending_pings["agent1"] = time.time()
        hb.handle_pong("agent1")
        assert "agent1" not in hb.pending_pings

    def test_resets_missed_count(self, hb):
        hb.missed_pings["agent1"] = 2
        hb.handle_pong("agent1")
        assert hb.missed_pings["agent1"] == 0


class TestMarkOffline:
    def test_sets_missed_to_three(self, hb):
        hb.mark_offline("agent1")
        assert hb.missed_pings["agent1"] == 3

    def test_clears_pending_ping(self, hb):
        hb.pending_pings["agent1"] = time.time()
        hb.mark_offline("agent1")
        assert "agent1" not in hb.pending_pings


class TestGetConnectionStatus:
    def test_active_when_no_misses(self, hb):
        assert hb.get_connection_status("agent1") == AgentConnectionStatus.ACTIVE

    def test_unresponsive_after_one_miss(self, hb):
        hb.missed_pings["agent1"] = 1
        assert hb.get_connection_status("agent1") == AgentConnectionStatus.UNRESPONSIVE

    def test_offline_after_three_misses(self, hb):
        hb.missed_pings["agent1"] = 3
        assert hb.get_connection_status("agent1") == AgentConnectionStatus.OFFLINE


class TestSendHeartbeats:
    @pytest.mark.asyncio
    async def test_sends_ping_to_all_connections(self, hb, mgr):
        mgr.active_connections = {"a1": MagicMock(), "a2": MagicMock()}
        await hb._send_heartbeats()
        assert mgr.send.call_count == 2
        assert "a1" in hb.pending_pings
        assert "a2" in hb.pending_pings


class TestStartStop:
    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, hb):
        await hb.start_heartbeat(interval=999)
        assert hb._task is not None
        await hb.stop()
        assert hb._task is None
