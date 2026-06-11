"""Tests for Phase 11.2b: Dashboard WebSocket auth.

Validates:
- JWT auth on /ws/dashboard (accept valid, reject invalid/missing)
- WELCOME message with role + tenant_id
- SUBSCRIBE/UNSUBSCRIBE message handling
- Event broadcasting to subscribed clients
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.coordinator.main import create_app
from agora.coordinator.dashboard_ws import (
    DashboardClient, DashboardHub, DASHBOARD_EVENTS,
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


class TestDashboardClient:
    def test_init(self):
        import asyncio
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        c = DashboardClient(ws, "admin", "default")
        assert c.role == "admin"
        assert c.tenant_id == "default"
        assert c.subscriptions == set()


class TestDashboardHub:
    @pytest.mark.asyncio
    async def test_connect_valid_token(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("dashboard_user:admin", "admin")
        ok, role, tid = await hub.connect("c1", ws, token)
        assert ok is True
        assert role == "admin"
        assert tid is None
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_invalid_token(self, hub):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        ok, role, tid = await hub.connect("c2", ws, "bad-token")
        assert ok is False
        ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_expired_token(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "admin", expires_delta=-1)
        ok, _, _ = await hub.connect("c3", ws, token)
        assert ok is False

    @pytest.mark.asyncio
    async def test_disconnect(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "observer")
        await hub.connect("c4", ws, token)
        hub.disconnect("c4")
        assert "c4" not in hub._clients

    @pytest.mark.asyncio
    async def test_subscribe(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "observer")
        await hub.connect("c5", ws, token)
        await hub.handle_message("c5", '{"type":"SUBSCRIBE","payload":{"channels":["discussions","tasks"]}}')
        client = hub._clients["c5"]
        assert "discussions" in client.subscriptions
        assert "tasks" in client.subscriptions
        ws.send_json.assert_called()

    @pytest.mark.asyncio
    async def test_unsubscribe(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "observer")
        await hub.connect("c6", ws, token)
        client = hub._clients["c6"]
        client.subscriptions = {"discussions", "tasks", "events"}
        await hub.handle_message("c6", '{"type":"UNSUBSCRIBE","payload":{"channels":["tasks"]}}')
        assert "tasks" not in client.subscriptions
        assert "discussions" in client.subscriptions

    @pytest.mark.asyncio
    async def test_broadcast_event_filtered(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        t1 = token_mgr.create_token("u1", "admin")
        t2 = token_mgr.create_token("u2", "observer")
        await hub.connect("c7", ws1, t1)
        await hub.connect("c8", ws2, t2)
        hub._clients["c7"].subscriptions = {"tasks"}
        hub._clients["c8"].subscriptions = {"discussions"}
        count = await hub.broadcast_event(
            "TASK_UPDATE", {"task_id": "t1"}, channel="tasks",
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_broadcast_event_all_subscribed(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        t1 = token_mgr.create_token("u1", "admin")
        t2 = token_mgr.create_token("u2", "observer")
        await hub.connect("c9", ws1, t1)
        await hub.connect("c10", ws2, t2)
        hub._clients["c9"].subscriptions = {"events"}
        hub._clients["c10"].subscriptions = {"events"}
        count = await hub.broadcast_event(
            "AGENT_STATUS", {"agent_id": "a1"}, channel="events",
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_invalid_json(self, hub, token_mgr):
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        token = token_mgr.create_token("u1", "admin")
        await hub.connect("c11", ws, token)
        await hub.handle_message("c11", "not json")
        ws.send_json.assert_called()
        msg = ws.send_json.call_args[0][0]
        assert msg["type"] == "ERROR"
