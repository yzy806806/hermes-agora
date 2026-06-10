"""Tests for agora/coordinator/plugin.py (Phase 10.3a)."""

import pytest

from agora.coordinator.plugin import (
    AgoraPlugin,
    HookContext,
    HookPoint,
    PluginManifest,
)


# -- HookPoint enum tests --


class TestHookPoint:
    def test_all_values_are_strings(self):
        for hp in HookPoint:
            assert isinstance(hp.value, str)

    def test_required_hook_points_exist(self):
        expected = [
            "DISCUSSION_CREATED", "DISCUSSION_ENDED",
            "TASK_CREATED", "TASK_COMPLETED", "TASK_FAILED",
            "AGENT_REGISTERED", "AGENT_DISCONNECTED",
            "MOTION_PASSED", "MOTION_REJECTED", "CUSTOM",
        ]
        for name in expected:
            assert hasattr(HookPoint, name)

    def test_dot_notation_values(self):
        assert HookPoint.DISCUSSION_CREATED.value == "discussion.created"
        assert HookPoint.TASK_FAILED.value == "task.failed"
        assert HookPoint.CUSTOM.value == "custom"


# -- HookContext model tests --


class TestHookContext:
    def test_defaults(self):
        ctx = HookContext(hook_point=HookPoint.TASK_CREATED)
        assert ctx.data == {}
        assert ctx.agent_id is None
        assert ctx.tenant_id is None
        assert ctx.timestamp is not None

    def test_with_all_fields(self):
        ctx = HookContext(
            hook_point=HookPoint.AGENT_REGISTERED,
            data={"agent_name": "test"},
            agent_id="a1",
            tenant_id="t1",
        )
        assert ctx.data["agent_name"] == "test"
        assert ctx.agent_id == "a1"
        assert ctx.tenant_id == "t1"


# -- PluginManifest model tests --


class TestPluginManifest:
    def test_required_fields(self):
        m = PluginManifest(name="test-plugin", version="1.0.0")
        assert m.name == "test-plugin"
        assert m.version == "1.0.0"

    def test_defaults(self):
        m = PluginManifest(name="p", version="0.1.0")
        assert m.description == ""
        assert m.author == ""
        assert m.hook_points == []
        assert m.dependencies == []
        assert m.min_agora_version == "0.10.0"

    def test_with_hooks(self):
        m = PluginManifest(
            name="gh-webhook",
            version="2.0.0",
            hook_points=[HookPoint.DISCUSSION_CREATED, HookPoint.TASK_COMPLETED],
        )
        assert len(m.hook_points) == 2


# -- AgoraPlugin ABC tests --


class _DummyPlugin(AgoraPlugin):
    """Concrete plugin for testing."""

    manifest = PluginManifest(name="dummy", version="0.1.0")
    loaded = False
    unloaded = False

    async def on_load(self, coordinator):
        self.loaded = True

    async def on_unload(self):
        self.unloaded = True


class TestAgoraPlugin:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            AgoraPlugin()

    @pytest.mark.asyncio
    async def test_concrete_plugin_lifecycle(self):
        p = _DummyPlugin()
        assert not p.loaded
        await p.on_load(coordinator=None)
        assert p.loaded
        await p.on_unload()
        assert p.unloaded

    @pytest.mark.asyncio
    async def test_health_check_default(self):
        p = _DummyPlugin()
        assert await p.health_check() is True

    @pytest.mark.asyncio
    async def test_hook_methods_are_noop(self):
        p = _DummyPlugin()
        ctx = HookContext(hook_point=HookPoint.TASK_CREATED)
        # All hook methods should run without error
        await p.on_discussion_created(ctx)
        await p.on_discussion_ended(ctx)
        await p.on_task_created(ctx)
        await p.on_task_completed(ctx)
        await p.on_task_failed(ctx)
        await p.on_agent_registered(ctx)
        await p.on_agent_disconnected(ctx)
        await p.on_motion_passed(ctx)
        await p.on_motion_rejected(ctx)

    def test_manifest_class_attribute(self):
        p = _DummyPlugin()
        assert p.manifest.name == "dummy"
        assert p.manifest.version == "0.1.0"
