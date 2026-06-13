"""Tests for Phase 13.2a: Dashboard WS broadcast fan-out.

Validates:
- Channel-based filtering in broadcast_event
- Project-based filtering in broadcast_event
- Combined channel + project filtering
- Stale client cleanup on send failure
- No project filter when client has no project subscriptions
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agora.coordinator.dashboard_ws import (
    CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS, CHANNEL_PIPELINES,
    DashboardHub,
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


async def _add_client(hub, token_mgr, cid, channels=None, projects=None):
    ws = AsyncMock()
    token = token_mgr.create_token(f"u_{cid}", "admin")
    await hub.connect(cid, ws, token)
    client = hub._clients[cid]
    if channels:
        client.subscriptions = set(channels)
    if projects:
        client.project_subscriptions = set(projects)
    return ws


class TestBroadcastChannelFilter:
    @pytest.mark.asyncio
    async def test_only_subscribed_channel_receives(self, hub, token_mgr):
        await _add_client(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        await _add_client(hub, token_mgr, "c2", channels={CHANNEL_PIPELINES})
        count = await hub.broadcast_event(
            "TASK_UPDATE", {"task_id": "t1"}, channel=CHANNEL_EVENTS,
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_all_subscribed_receive(self, hub, token_mgr):
        await _add_client(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        await _add_client(hub, token_mgr, "c2", channels={CHANNEL_EVENTS})
        count = await hub.broadcast_event(
            "AGENT_STATUS", {"agent_id": "a1"}, channel=CHANNEL_EVENTS,
        )
        assert count == 2


class TestBroadcastProjectFilter:
    @pytest.mark.asyncio
    async def test_project_filter_match(self, hub, token_mgr):
        await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_EVENTS}, projects={"proj1"},
        )
        count = await hub.broadcast_event(
            "TASK_UPDATE",
            {"task_id": "t1", "project_id": "proj1"},
            channel=CHANNEL_EVENTS,
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_project_filter_no_match(self, hub, token_mgr):
        await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_EVENTS}, projects={"proj1"},
        )
        count = await hub.broadcast_event(
            "TASK_UPDATE",
            {"task_id": "t1", "project_id": "proj2"},
            channel=CHANNEL_EVENTS,
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_no_project_subs_receives_all(self, hub, token_mgr):
        """Client with no project_subscriptions gets all events."""
        await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_EVENTS}, projects=set(),
        )
        count = await hub.broadcast_event(
            "TASK_UPDATE",
            {"task_id": "t1", "project_id": "proj_any"},
            channel=CHANNEL_EVENTS,
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_event_without_project_id(self, hub, token_mgr):
        """Events without project_id go to all channel subscribers."""
        await _add_client(
            hub, token_mgr, "c1",
            channels={CHANNEL_EVENTS}, projects={"proj1"},
        )
        count = await hub.broadcast_event(
            "AGENT_STATUS", {"agent_id": "a1"}, channel=CHANNEL_EVENTS,
        )
        assert count == 1


class TestStaleClientCleanup:
    @pytest.mark.asyncio
    async def test_stale_client_removed_on_send_failure(self, hub, token_mgr):
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "admin")
        await hub.connect("c1", ws, token)
        hub._clients["c1"].subscriptions = {CHANNEL_EVENTS}
        # Make send fail
        ws.send_json.side_effect = RuntimeError("connection lost")
        count = await hub.broadcast_event(
            "TASK_UPDATE", {"task_id": "t1"}, channel=CHANNEL_EVENTS,
        )
        assert count == 0
        assert "c1" not in hub._clients
