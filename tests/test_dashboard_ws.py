"""Phase 13.2d: Dashboard WS fan-out & subscription filtering tests.

Validates:
- Event fan-out to multiple subscribed clients
- No event to unsubscribed clients
- Subscription filtering: only events for subscribed project
- Mixed channel + project subscription scenarios
- Client with no project subs receives all project events
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


class TestFanOut:
    """Event fan-out to multiple clients."""

    @pytest.mark.asyncio
    async def test_fanout_to_all_subscribed(self, hub, token_mgr):
        w1 = await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        w2 = await _add(hub, token_mgr, "c2", channels={CHANNEL_EVENTS})
        w3 = await _add(hub, token_mgr, "c3", channels={CHANNEL_EVENTS})
        n = await hub.broadcast_event("TASK_UPDATE", {"t": "1"}, CHANNEL_EVENTS)
        assert n == 3
        for w in (w1, w2, w3):
            w.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_fanout_skips_unsubscribed(self, hub, token_mgr):
        w1 = await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        w2 = await _add(hub, token_mgr, "c2", channels={CHANNEL_PIPELINES})
        n = await hub.broadcast_event("TASK_UPDATE", {"t": "1"}, CHANNEL_EVENTS)
        assert n == 1
        w1.send_json.assert_called_once()
        w2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_fanout_mixed_channels(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1", channels={CHANNEL_EVENTS})
        await _add(hub, token_mgr, "c2", channels={CHANNEL_NOTIFICATIONS})
        ne = await hub.broadcast_event("T", {}, CHANNEL_EVENTS)
        nn = await hub.broadcast_event("N", {}, CHANNEL_NOTIFICATIONS)
        assert ne == 1
        assert nn == 1


class TestProjectFilter:
    """Subscription filtering by project_id."""

    @pytest.mark.asyncio
    async def test_only_matching_project_receives(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1",
                   channels={CHANNEL_EVENTS}, projects={"proj1"})
        await _add(hub, token_mgr, "c2",
                   channels={CHANNEL_EVENTS}, projects={"proj2"})
        n = await hub.broadcast_event(
            "TASK_UPDATE", {"project_id": "proj1"}, CHANNEL_EVENTS)
        assert n == 1

    @pytest.mark.asyncio
    async def test_no_project_subs_gets_all(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1",
                   channels={CHANNEL_EVENTS}, projects=set())
        n = await hub.broadcast_event(
            "TASK_UPDATE", {"project_id": "any"}, CHANNEL_EVENTS)
        assert n == 1

    @pytest.mark.asyncio
    async def test_multi_project_client_gets_both(self, hub, token_mgr):
        await _add(hub, token_mgr, "c1",
                   channels={CHANNEL_EVENTS}, projects={"p1", "p2"})
        n1 = await hub.broadcast_event(
            "T", {"project_id": "p1"}, CHANNEL_EVENTS)
        n2 = await hub.broadcast_event(
            "T", {"project_id": "p2"}, CHANNEL_EVENTS)
        assert n1 == 1
        assert n2 == 1
