"""Tests for Phase 11.1c: Plugin management action endpoints."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agora.coordinator.plugin import AgoraPlugin, PluginManifest
from agora.coordinator.plugin_manager import PluginCoordinator
from agora.coordinator.plugin_routes_actions import (
    init_plugin_action_deps, router,
)


class DummyPlugin(AgoraPlugin):
    """Minimal plugin for testing."""
    manifest = PluginManifest(
        name="action-test-plugin", version="1.0.0",
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
    init_plugin_action_deps(coord)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestReloadPlugin:
    def test_reload_found(self, client):
        r = client.post("/api/v1/admin/plugins/action-test-plugin/reload")
        assert r.status_code == 200
        assert r.json()["status"] == "reloaded"

    def test_reload_not_found(self, client):
        r = client.post("/api/v1/admin/plugins/nonexistent/reload")
        assert r.status_code == 404


class TestDisablePlugin:
    def test_disable_found(self, client, coord):
        r = client.post("/api/v1/admin/plugins/action-test-plugin/disable")
        assert r.status_code == 200
        assert r.json()["status"] == "disabled"
        assert coord.get_plugin("action-test-plugin") is None

    def test_disable_not_found(self, client):
        r = client.post("/api/v1/admin/plugins/nonexistent/disable")
        assert r.status_code == 404


class TestEnablePlugin:
    def test_enable_not_available(self, client):
        r = client.post("/api/v1/admin/plugins/nonexistent/enable")
        assert r.status_code == 404
