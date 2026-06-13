"""Dashboard WS handle_message tests — Phase 13.2d regression restore.

SUBSCRIBE, UNSUBSCRIBE, SUBSCRIBE_PROJECT, UNSUBSCRIBE_PROJECT,
invalid JSON, unknown type, missing client."""
from __future__ import annotations
import json
import pytest
from unittest.mock import AsyncMock
from agora.coordinator.dashboard_ws import (
    CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS, DashboardHub,
)
from agora.coordinator.models import MessageType
from agora.coordinator.token_manager import TokenManager

@pytest.fixture
def tmgr():
    return TokenManager(secret="test-secret-key")

@pytest.fixture
def hub(tmgr):
    h = DashboardHub()
    h.set_token_manager(tmgr)
    return h

async def _connect(hub, tmgr, cid):
    ws = AsyncMock()
    token = tmgr.create_token(f"u_{cid}", "admin")
    ok, _, _ = await hub.connect(cid, ws, token)
    assert ok
    return ws

class TestHandleMessage:
    @pytest.mark.asyncio
    async def test_subscribe(self, hub, tmgr):
        await _connect(hub, tmgr, "c1")
        await hub.handle_message("c1", json.dumps(
            {"type": "SUBSCRIBE",
             "payload": {"channels": [CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS]}}))
        assert hub._clients["c1"].subscriptions == {CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS}

    @pytest.mark.asyncio
    async def test_unsubscribe(self, hub, tmgr):
        await _connect(hub, tmgr, "c1")
        c = hub._clients["c1"]
        c.subscriptions = {CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS}
        await hub.handle_message("c1", json.dumps(
            {"type": "UNSUBSCRIBE", "payload": {"channels": [CHANNEL_EVENTS]}}))
        assert c.subscriptions == {CHANNEL_NOTIFICATIONS}

    @pytest.mark.asyncio
    async def test_subscribe_project(self, hub, tmgr):
        await _connect(hub, tmgr, "c1")
        await hub.handle_message("c1", json.dumps(
            {"type": "SUBSCRIBE_PROJECT", "payload": {"project_ids": ["p1", "p2"]}}))
        assert hub._clients["c1"].project_subscriptions == {"p1", "p2"}

    @pytest.mark.asyncio
    async def test_unsubscribe_project(self, hub, tmgr):
        await _connect(hub, tmgr, "c1")
        hub._clients["c1"].project_subscriptions = {"p1", "p2"}
        await hub.handle_message("c1", json.dumps(
            {"type": "UNSUBSCRIBE_PROJECT", "payload": {"project_ids": ["p1"]}}))
        assert hub._clients["c1"].project_subscriptions == {"p2"}

    @pytest.mark.asyncio
    async def test_invalid_json(self, hub, tmgr):
        ws = await _connect(hub, tmgr, "c1")
        await hub.handle_message("c1", "not-json{{{")
        ws.send_json.assert_called_once_with({
            "type": MessageType.ERROR,
            "payload": {"code": "invalid_json", "message": "Bad JSON"}})

    @pytest.mark.asyncio
    async def test_unknown_type_ignored(self, hub, tmgr):
        await _connect(hub, tmgr, "c1")
        await hub.handle_message("c1", json.dumps({"type": "UNKNOWN"}))
        assert hub._clients["c1"].subscriptions == set()

    @pytest.mark.asyncio
    async def test_missing_client_ignored(self, hub, tmgr):
        await hub.handle_message("ghost", json.dumps({"type": "SUBSCRIBE"}))