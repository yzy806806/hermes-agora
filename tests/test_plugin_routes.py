"""Tests for Phase 11.1c: Plugin management read endpoints."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agora.coordinator.plugin import AgoraPlugin, HookPoint, PluginManifest
from agora.coordinator.plugin_manager import PluginCoordinator
from agora.coordinator.plugin_routes import (
    init_plugin_route_deps, router,
)


class DummyPlugin(AgoraPlugin):
    """Minimal plugin for testing."""
    manifest = PluginManifest(
        name="test-plugin", version="1.0.0",
        description="A test plugin",
    )

    async def on_load(self, coordinator):
        pass

    async def on_unload(self):
        pass


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def coord():
    return PluginCoordinator()


@pytest.fixture
def app(coord):
    _run(coord.load_plugin(DummyPlugin()))
    init_plugin_route_deps(coord)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestListPlugins:
    def test_empty(self, coord):
        init_plugin_route_deps(coord)
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        c = TestClient(app)
        r = c.get("/api/v1/admin/plugins")
        assert r.status_code == 200
        assert r.json() == []

    def test_with_plugin(self, client):
        r = client.get("/api/v1/admin/plugins")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-plugin"


class TestGetPluginDetail:
    def test_found(self, client):
        r = client.get("/api/v1/admin/plugins/test-plugin")
        assert r.status_code == 200
        assert r.json()["name"] == "test-plugin"

    def test_not_found(self, client):
        r = client.get("/api/v1/admin/plugins/nonexistent")
        assert r.status_code == 404


class TestListAvailablePlugins:
    def test_available(self, client):
        r = client.get("/api/v1/admin/plugins/available")
        assert r.status_code == 200
        # test-plugin is already loaded, so not available
        assert isinstance(r.json(), list)
