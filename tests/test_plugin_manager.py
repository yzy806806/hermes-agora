"""Tests for plugin_manager.py (Phase 10.3b)."""
from __future__ import annotations

import asyncio
import pytest

from agora.coordinator.plugin import (
    AgoraPlugin, HookContext, HookPoint, PluginManifest,
)
from agora.coordinator.plugin_manager import PluginCoordinator


class _GoodPlugin(AgoraPlugin):
    def __init__(self) -> None:
        self.manifest = PluginManifest(
            name="good", version="1.0", description="test",
            author="test", hook_points=[HookPoint.DISCUSSION_CREATED],
        )
        self.loaded = False
        self.unloaded = False

    async def on_load(self, coordinator: PluginCoordinator) -> None:
        self.loaded = True

    async def on_unload(self) -> None:
        self.unloaded = True

    async def on_discussion_created(self, ctx: HookContext) -> None:
        self.hook_called = True


class _BadLoadPlugin(AgoraPlugin):
    def __init__(self) -> None:
        self.manifest = PluginManifest(
            name="bad_load", version="1.0", description="test",
        )

    async def on_load(self, coordinator: PluginCoordinator) -> None:
        raise RuntimeError("load failed")

    async def on_unload(self) -> None:
        pass


class _UnhealthyPlugin(AgoraPlugin):
    def __init__(self) -> None:
        self.manifest = PluginManifest(
            name="unhealthy", version="1.0", description="test",
        )

    async def on_load(self, coordinator: PluginCoordinator) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    async def health_check(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_load_plugin():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    await coord.load_plugin(p)
    assert p.loaded
    assert coord.get_plugin("good") is p


@pytest.mark.asyncio
async def test_load_duplicate():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    await coord.load_plugin(p)
    await coord.load_plugin(p)
    assert len(coord.list_plugins()) == 1


@pytest.mark.asyncio
async def test_load_failure():
    coord = PluginCoordinator()
    p = _BadLoadPlugin()
    await coord.load_plugin(p)
    assert coord.get_plugin("bad_load") is None


@pytest.mark.asyncio
async def test_unload_plugin():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    await coord.load_plugin(p)
    await coord.unload_plugin("good")
    assert p.unloaded
    assert coord.get_plugin("good") is None


@pytest.mark.asyncio
async def test_unload_missing():
    coord = PluginCoordinator()
    await coord.unload_plugin("nonexistent")


@pytest.mark.asyncio
async def test_fire_hook():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    await coord.load_plugin(p)
    ctx = HookContext(hook_point=HookPoint.DISCUSSION_CREATED)
    await coord.fire_hook(HookPoint.DISCUSSION_CREATED, ctx)
    await asyncio.sleep(0.05)
    assert p.hook_called


@pytest.mark.asyncio
async def test_fire_hook_no_handlers():
    coord = PluginCoordinator()
    ctx = HookContext(hook_point=HookPoint.AGENT_REGISTERED)
    await coord.fire_hook(HookPoint.AGENT_REGISTERED, ctx)


@pytest.mark.asyncio
async def test_health_check_all():
    coord = PluginCoordinator()
    good = _GoodPlugin()
    good.hook_called = False
    bad = _UnhealthyPlugin()
    await coord.load_plugin(good)
    await coord.load_plugin(bad)
    results = await coord.health_check_all()
    assert results["good"] is True
    assert results["unhealthy"] is False
    assert coord.get_plugin("unhealthy") is None


@pytest.mark.asyncio
async def test_list_plugins():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    await coord.load_plugin(p)
    manifests = coord.list_plugins()
    assert len(manifests) == 1
    assert manifests[0].name == "good"


@pytest.mark.asyncio
async def test_register_hook_explicit():
    coord = PluginCoordinator()
    p = _GoodPlugin()
    p.hook_called = False
    called = []

    async def handler(ctx: HookContext) -> None:
        called.append(True)

    coord.register_hook(p, HookPoint.AGENT_REGISTERED, handler)
    ctx = HookContext(hook_point=HookPoint.AGENT_REGISTERED)
    await coord.fire_hook(HookPoint.AGENT_REGISTERED, ctx)
    await asyncio.sleep(0.05)
    assert called
