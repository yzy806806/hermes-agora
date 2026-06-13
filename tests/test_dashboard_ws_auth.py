"""Dashboard WS auth & init tests (restored from Phase 13.2d regression).

Covers: token auth (valid/invalid/expired), no token manager,
DashboardClient.__init__.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agora.coordinator.dashboard_ws import DashboardClient, DashboardHub
from agora.coordinator.token_manager import TokenManager


@pytest.fixture
def tmgr():
    return TokenManager(secret="test-secret-key")


@pytest.fixture
def hub(tmgr):
    h = DashboardHub()
    h.set_token_manager(tmgr)
    return h


class TestConnectAuth:
    @pytest.mark.asyncio
    async def test_connect_valid_token(self, hub, tmgr):
        ws = AsyncMock()
        token = tmgr.create_token("u1", "admin")
        ok, role, tid = await hub.connect("c1", ws, token)
        assert ok and role == "admin"
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_invalid_token(self, hub, tmgr):
        ws = AsyncMock()
        ok, role, tid = await hub.connect("c1", ws, "bad-token")
        assert not ok
        reason = ws.close.call_args[1]["reason"]
        assert "Invalid token" in reason

    @pytest.mark.asyncio
    async def test_connect_expired_token(self, hub, tmgr):
        ws = AsyncMock()
        token = tmgr.create_token("u1", "admin", expires_delta=-1)
        ok, _, _ = await hub.connect("c1", ws, token)
        assert not ok
        reason = ws.close.call_args[1]["reason"]
        assert "Invalid token" in reason

    @pytest.mark.asyncio
    async def test_connect_no_token_manager(self):
        hub = DashboardHub()  # no set_token_manager
        ws = AsyncMock()
        ok, _, _ = await hub.connect("c1", ws, "any")
        assert not ok
        ws.close.assert_called_once_with(code=1011, reason="Server not initialized")


class TestInit:
    def test_dashboard_client_init(self):
        ws = AsyncMock()
        c = DashboardClient(ws, role="viewer", tenant_id="t1")
        assert c.role == "viewer"
        assert c.tenant_id == "t1"
        assert c.subscriptions == set()
        assert c.project_subscriptions == set()
