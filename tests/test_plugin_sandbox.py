"""Tests for plugin_sandbox.py — import blocking, timeout, memory limits."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from agora.coordinator.plugin import AgoraPlugin, PluginManifest
from agora.coordinator.plugin_sandbox import (
    PluginSandbox,
    sandbox_context,
)


class _DummyPlugin(AgoraPlugin):
    """Minimal concrete plugin for testing."""

    manifest = PluginManifest(
        name="test-plugin", version="0.1.0",
        description="test", author="tester",
    )

    async def on_load(self, coordinator):
        pass

    async def on_unload(self):
        pass


@pytest.fixture
def plugin():
    return _DummyPlugin()


@pytest.fixture
def sandbox(plugin):
    return PluginSandbox(plugin)


class TestCheckImport:
    def test_blocked_os(self, sandbox):
        assert sandbox.check_import("os") is False

    def test_blocked_subprocess(self, sandbox):
        assert sandbox.check_import("subprocess") is False

    def test_blocked_socket(self, sandbox):
        assert sandbox.check_import("socket") is False

    def test_blocked_ctypes(self, sandbox):
        assert sandbox.check_import("ctypes") is False

    def test_allowed_json(self, sandbox):
        assert sandbox.check_import("json") is True

    def test_allowed_submodule_os_path(self, sandbox):
        assert sandbox.check_import("os.path") is False

    def test_allowed_agora(self, sandbox):
        assert sandbox.check_import("agora") is True

    def test_custom_blocked_imports(self, plugin):
        sb = PluginSandbox(plugin, blocked_imports={"sys", "builtins"})
        assert sb.check_import("sys") is False
        assert sb.check_import("os") is True


class TestEnforceTimeout:
    @pytest.mark.asyncio
    async def test_completes_within_timeout(self, sandbox):
        async def quick():
            return "done"

        result = await sandbox.enforce_timeout(quick())
        assert result == "done"

    @pytest.mark.asyncio
    async def test_exceeds_timeout(self, sandbox):
        async def slow():
            await asyncio.sleep(60)

        with pytest.raises(asyncio.TimeoutError):
            await sandbox.enforce_timeout(slow(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_custom_timeout(self, sandbox):
        sandbox.timeout_seconds = 1
        async def moderate():
            await asyncio.sleep(0.05)
            return "ok"

        result = await sandbox.enforce_timeout(moderate())
        assert result == "ok"


class TestMemoryLimit:
    def test_set_memory_limit(self, sandbox):
        sandbox.set_memory_limit(200)
        assert sandbox.memory_limit_mb == 200

    def test_memory_exceeded_default(self, sandbox):
        assert sandbox.memory_exceeded is False


class TestSandboxContext:
    @pytest.mark.asyncio
    async def test_context_yields_sandbox(self, sandbox):
        async with sandbox_context(sandbox) as sb:
            assert sb is sandbox

    @pytest.mark.asyncio
    async def test_context_no_crash(self, sandbox):
        async with sandbox_context(sandbox):
            pass  # no error
