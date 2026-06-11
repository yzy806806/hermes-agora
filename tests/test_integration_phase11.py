"""Integration tests for Phase 11.5a: wiring + backward compat.

Tests:
- Auth login endpoint (configured / not configured)
- Event bus publish
- All routers registered in app
- Backward compat: dashboard accessible without auth
"""
from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from agora.coordinator.main import create_app
from agora.coordinator.storage import Storage
from agora.coordinator.state import StateMachine
from agora.coordinator.dashboard import init_dashboard_deps
from agora.coordinator.router import init_deps
from agora.coordinator.auth_router import init_auth_deps
from agora.coordinator.event_bus import init_event_bus, publish
from agora.coordinator.dashboard_ws import DashboardHub
from agora.coordinator.token_manager import TokenManager


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_phase11.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest_asyncio.fixture(loop_scope="session")
async def app_no_auth(storage):
    """App without AGORA_DASHBOARD_USERS (backward compat)."""
    app = create_app()
    sm = StateMachine(storage)
    init_deps(storage, sm)
    init_dashboard_deps(storage)
    token_mgr = TokenManager(secret="test-secret")
    init_auth_deps(token_mgr)
    hub = DashboardHub()
    hub.set_token_manager(token_mgr)
    init_event_bus(hub)
    return app


@pytest_asyncio.fixture(loop_scope="session")
async def client_no_auth(app_no_auth):
    transport = ASGITransport(app=app_no_auth)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Auth login tests ---


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_login_not_configured(client_no_auth):
    """Login returns 501 when AGORA_DASHBOARD_USERS not set."""
    resp = await client_no_auth.post("/api/v1/auth/login", json={
        "username": "admin", "password": "test",
    })
    assert resp.status_code == 501
    assert "not configured" in resp.json()["detail"].lower()


@pytest.mark.asyncio(loop_scope="session")
async def test_auth_login_with_users(monkeypatch):
    """Login succeeds when AGORA_DASHBOARD_USERS is set."""
    from agora.coordinator import config
    monkeypatch.setattr(config.settings, "dashboard_users",
                        "admin:testpass,viewer:viewpass")
    app = create_app()
    storage = Storage(":memory:")
    await storage.init_db()
    sm = StateMachine(storage)
    init_deps(storage, sm)
    init_dashboard_deps(storage)
    token_mgr = TokenManager(secret="test-secret")
    init_auth_deps(token_mgr)
    hub = DashboardHub()
    hub.set_token_manager(token_mgr)
    init_event_bus(hub)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/login", json={
            "username": "admin", "password": "testpass",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["role"] == "admin"
