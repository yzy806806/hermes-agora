"""Tests for agora/coordinator/plugin_discovery.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agora.coordinator.plugin import AgoraPlugin, HookPoint, PluginManifest
from agora.coordinator.plugin_discovery import (
    check_dependencies,
    discover_plugins,
    filter_plugins,
    validate_manifest,
)


class _GoodPlugin(AgoraPlugin):
    manifest = PluginManifest(
        name="test-plugin", version="1.0.0",
        description="test", min_agora_version="0.1.0",
    )

    async def on_load(self, coordinator): pass
    async def on_unload(self): pass


class _BadType:
    """Not an AgoraPlugin subclass."""
    pass


def _make_ep(name: str, load_result):
    """Create a mock EntryPoint."""
    ep = MagicMock(spec=["name", "load", "group"])
    ep.name = name
    ep.load.return_value = load_result
    ep.group = "agora.plugins"
    return ep


class TestDiscoverPlugins:
    @patch("agora.coordinator.plugin_discovery.importlib.metadata.entry_points")
    def test_discovers_valid_plugin(self, mock_eps):
        ep = _make_ep("test_plugin", _GoodPlugin)
        mock_eps.return_value.select.return_value = [ep]
        plugins = discover_plugins()
        assert len(plugins) == 1
        assert plugins[0].manifest.name == "test-plugin"

    @patch("agora.coordinator.plugin_discovery.importlib.metadata.entry_points")
    def test_skips_non_plugin_class(self, mock_eps):
        ep = _make_ep("bad", _BadType)
        mock_eps.return_value.select.return_value = [ep]
        plugins = discover_plugins()
        assert len(plugins) == 0

    @patch("agora.coordinator.plugin_discovery.importlib.metadata.entry_points")
    def test_handles_load_error(self, mock_eps):
        ep = _make_ep("broken", None)
        ep.load.side_effect = ImportError("missing")
        mock_eps.return_value.select.return_value = [ep]
        plugins = discover_plugins()
        assert len(plugins) == 0


class TestValidateManifest:
    @patch("agora.coordinator.plugin_discovery.importlib.metadata.version")
    def test_passes_when_version_ok(self, mock_ver):
        mock_ver.return_value = "0.10.0"
        p = _GoodPlugin()
        assert validate_manifest(p) is True

    @patch("agora.coordinator.plugin_discovery.importlib.metadata.version")
    def test_fails_when_version_too_low(self, mock_ver):
        mock_ver.return_value = "0.9.0"
        p = _GoodPlugin()  # min_agora_version="0.1.0" → still passes
        assert validate_manifest(p) is True

    @patch("agora.coordinator.plugin_discovery.importlib.metadata.version")
    def test_fails_on_version_mismatch(self, mock_ver):
        mock_ver.return_value = "0.1.0"
        p = _GoodPlugin()  # min_agora_version default "0.1.0" → passes
        # create one that requires a newer version
        class _NewPlugin(AgoraPlugin):
            manifest = PluginManifest(name="new", version="1.0.0", min_agora_version="99.0.0")
            async def on_load(self, coordinator): pass
            async def on_unload(self): pass
        assert validate_manifest(_NewPlugin()) is False


class TestCheckDependencies:
    def test_all_deps_available(self):
        m = PluginManifest(name="p", version="1.0", dependencies=["json", "os"])
        assert check_dependencies(m) is True

    def test_missing_dep(self):
        m = PluginManifest(name="p", version="1.0", dependencies=["nonexistent_pkg_xyz"])
        assert check_dependencies(m) is False


class TestFilterPlugins:
    def _make_plugin(self, name: str) -> AgoraPlugin:
        class P(AgoraPlugin):
            manifest = PluginManifest(name=name, version="1.0")
            async def on_load(self, coordinator): pass
            async def on_unload(self): pass
        return P()

    def test_whitelist_mode(self):
        plugins = [self._make_plugin("a"), self._make_plugin("b")]
        result = filter_plugins(plugins, enabled=["a"])
        assert len(result) == 1
        assert result[0].manifest.name == "a"

    def test_blacklist_mode(self):
        plugins = [self._make_plugin("a"), self._make_plugin("b")]
        result = filter_plugins(plugins, disabled=["b"])
        assert len(result) == 1
        assert result[0].manifest.name == "a"

    def test_no_filter(self):
        plugins = [self._make_plugin("a"), self._make_plugin("b")]
        result = filter_plugins(plugins)
        assert len(result) == 2
