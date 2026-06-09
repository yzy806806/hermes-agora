"""Tests for Phase 8.2 fix: lazy-init tenant deps on WS connect."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.ws import ConnectionManager, ConnectionHub
from agora.coordinator.ws_endpoint import websocket_endpoint


class TestLazyInitTenantDeps:
    """Non-default tenant hubs get deps injected on first WS connect."""

    @pytest.mark.asyncio
    async def test_non_default_hub_gets_deps_injected(self):
        """When hub._storage is None, deps are lazily initialized."""
        mgr = ConnectionManager()
        hub = mgr.get_hub("acme")
        assert hub._storage is None

        # Mock the module-level manager singleton
        with patch("agora.coordinator.ws_endpoint.manager", mgr):
            # Build a mock WebSocket with app.state.storage_mgr
            ws = MagicMock()
            ws.app.state.storage_mgr = AsyncMock()
            ws.app.state.storage_mgr.get_tenant_storage = AsyncMock(
                return_value=MagicMock()
            )
            # hub.connect will fail (no agent registered), but deps
            # should be set before connect is called
            hub.connect = AsyncMock(return_value=False)

            await websocket_endpoint(ws, "agent1", "acme")

            # storage_mgr.get_tenant_storage was called for "acme"
            ws.app.state.storage_mgr.get_tenant_storage.assert_awaited_once_with("acme")
            # hub now has deps
            assert hub._storage is not None
            assert hub._state_machine is not None

    @pytest.mark.asyncio
    async def test_default_hub_not_lazy_inited(self):
        """Default hub is NOT lazy-inited (handled by lifespan)."""
        mgr = ConnectionManager()
        hub = mgr.get_hub("default")
        assert hub._storage is None

        with patch("agora.coordinator.ws_endpoint.manager", mgr):
            ws = MagicMock()
            ws.app.state.storage_mgr = AsyncMock()
            hub.connect = AsyncMock(return_value=False)

            await websocket_endpoint(ws, "agent1", "default")

            # storage_mgr should NOT be called for default tenant
            ws.app.state.storage_mgr.get_tenant_storage.assert_not_awaited()
            # hub still has no deps
            assert hub._storage is None

    @pytest.mark.asyncio
    async def test_already_inited_hub_skips_lazy_init(self):
        """If hub already has deps, lazy-init is skipped."""
        mgr = ConnectionManager()
        hub = mgr.get_hub("acme")
        hub._storage = MagicMock()
        hub._state_machine = MagicMock()

        with patch("agora.coordinator.ws_endpoint.manager", mgr):
            ws = MagicMock()
            ws.app.state.storage_mgr = AsyncMock()
            hub.connect = AsyncMock(return_value=False)

            await websocket_endpoint(ws, "agent1", "acme")

            # storage_mgr should NOT be called — already inited
            ws.app.state.storage_mgr.get_tenant_storage.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_storage_mgr_graceful(self):
        """If app.state has no storage_mgr, no crash — just fails connect."""
        mgr = ConnectionManager()

        with patch("agora.coordinator.ws_endpoint.manager", mgr):
            ws = MagicMock()
            # No storage_mgr attribute
            del ws.app.state.storage_mgr
            hub = mgr.get_hub("acme")
            hub.connect = AsyncMock(return_value=False)

            await websocket_endpoint(ws, "agent1", "acme")

            # hub._storage still None, but no exception raised
            assert hub._storage is None
