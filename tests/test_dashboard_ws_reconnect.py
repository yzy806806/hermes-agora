"""Phase 13.2d: Dashboard WS reconnection & offline indicator tests.

Validates:
- Reconnection: client disconnects, reconnects, receives events again
- Reconnection: new client_id after reconnect, old one cleaned up
- Offline indicator: AGENT_OFFLINE event broadcast to dashboard clients
- Offline indicator: agent disconnect triggers event_bus publish
- Hub tracks connected_clients correctly across connect/disconnect cycles
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from agora.coordinator.dashboard_ws import (
    CHANNEL_EVENTS, DashboardHub,
)
from agora.coordinator.token_manager import TokenManager


@pytest.fixture
def token_mgr():
    return TokenManager(secret="test-secret-key")


@pytest.fixture
def hub(token_mgr):
    h = DashboardHub()
    h.set_token_manager(token_mgr)
    return h


async def _add(hub, tmgr, cid, channels=None, projects=None):
    ws = AsyncMock()
    token = tmgr.create_token(f"u_{cid}", "admin")
    await hub.connect(cid, ws, token)
    c = hub._clients[cid]
    if channels:
        c.subscriptions = set(channels)
    if projects:
        c.project_subscriptions = set(projects)
    return ws


class TestReconnection:
    """Client disconnects then reconnects."""

    @pytest.mark.asyncio
    async def test_reconnect_receives_events(self, hub, token_mgr):
        ws1 = await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        hub.disconnect("c1")
        assert "c1" not in hub._clients
        ws2 = await _add(hub, token_mgr, "c1b", channels={CHANNEL_EVENTS})
        n = await hub.broadcast_event("T", {}, CHANNEL_EVENTS)
        assert n == 1
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_stops_events(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        hub.disconnect("c1")
        n = await hub.broadcast_event("T", {}, CHANNEL_EVENTS)
        assert n == 0

    @pytest.mark.asyncio
    async def test_connected_clients_after_reconnect(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        assert hub.connected_clients == 1
        hub.disconnect("c1")
        assert hub.connected_clients == 0
        await _add(hub, token_mgr, "c1b", channels={CHANNEL_EVENTS})
        assert hub.connected_clients == 1


class TestOfflineIndicator:
    """AGENT_OFFLINE events pushed to dashboard clients."""

    @pytest.mark.asyncio
    async def test_offline_event_broadcast(self, hub, token_mgr):
        ws = await _add(hub, token_mgr, "d1", channels={CHANNEL_EVENTS})
        n = await hub.broadcast_event(
            "AGENT_OFFLINE",
            {"agent_id": "agent_1", "reason": "timeout"},
            CHANNEL_EVENTS,
        )
        assert n == 1
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "AGENT_OFFLINE"
        assert call_args["payload"]["agent_id"] == "agent_1"

    @pytest.mark.asyncio
    async def test_offline_event_filtered_by_project(self, hub, token_mgr):
        await _add(hub, token_mgr, "d1",
                   channels={CHANNEL_EVENTS}, projects={"proj1"})
        n = await hub.broadcast_event(
            "AGENT_OFFLINE",
            {"agent_id": "a1", "project_id": "proj2"},
            CHANNEL_EVENTS,
        )
        assert n == 0

    @pytest.mark.asyncio
    async def test_event_bus_publish_forwards(self, hub, token_mgr):
        from agora.coordinator.event_bus import init_event_bus, publish
        init_event_bus(hub)
        ws = await _add(hub, token_mgr, "d1", channels={CHANNEL_EVENTS})
        n = await publish("AGENT_OFFLINE", {"agent_id": "a1"})
        assert n == 1
