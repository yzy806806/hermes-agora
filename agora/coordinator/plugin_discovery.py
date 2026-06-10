"""Plugin discovery for the Agora Plugin Ecosystem (Phase 10.3c).

Scans installed packages for ``agora.plugins`` entry points using
importlib.metadata, validates manifests, checks dependencies, and
filters by config-based enable/disable lists.
"""
from __future__ import annotations

import importlib.metadata
import logging
from importlib.metadata import EntryPoint
from packaging.version import Version

from agora.coordinator.plugin import AgoraPlugin, PluginManifest

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "agora.plugins"


def discover_plugins() -> list[AgoraPlugin]:
    """Scan installed packages for agora.plugins entry points."""
    plugins: list[AgoraPlugin] = []
    eps = importlib.metadata.entry_points()
    # Python 3.12+ returns a SelectableGroups; 3.9+ may return dict
    group_eps = eps.select(group=ENTRY_POINT_GROUP) if hasattr(eps, "select") else eps.get(ENTRY_POINT_GROUP, [])
    for ep in group_eps:
        try:
            plugin_cls = ep.load()
            instance = plugin_cls()
            if not isinstance(instance, AgoraPlugin):
                logger.warning("Entry point %s is not an AgoraPlugin subclass", ep.name)
                continue
            plugins.append(instance)
            logger.info("Discovered plugin: %s v%s", instance.manifest.name, instance.manifest.version)
        except Exception:
            logger.exception("Failed to load plugin entry point: %s", ep.name)
    return plugins


def validate_manifest(plugin: AgoraPlugin) -> bool:
    """Check version compatibility and dependency availability."""
    manifest = plugin.manifest
    try:
        agora_ver = Version(importlib.metadata.version("agora"))
        min_ver = Version(manifest.min_agora_version)
        if agora_ver < min_ver:
            logger.warning(
                "Plugin %s requires agora>=%s, current %s",
                manifest.name, manifest.min_agora_version, agora_ver,
            )
            return False
    except importlib.metadata.PackageNotFoundError:
        logger.debug("agora package metadata not found; skipping version check")
    return check_dependencies(manifest)


def check_dependencies(manifest: PluginManifest) -> bool:
    """Verify all declared dependencies are importable."""
    for dep in manifest.dependencies:
        try:
            __import__(dep)
        except ImportError:
            logger.warning("Plugin %s missing dependency: %s", manifest.name, dep)
            return False
    return True


def filter_plugins(
    plugins: list[AgoraPlugin],
    enabled: list[str] | None = None,
    disabled: list[str] | None = None,
) -> list[AgoraPlugin]:
    """Filter discovered plugins by config enable/disable lists.

    If *enabled* is non-empty, only plugins whose manifest.name is in
    the list are kept (whitelist mode).  Otherwise all discovered
    plugins are candidates, minus any in *disabled* (blacklist).
    """
    disabled_set = set(disabled or [])
    if enabled is not None and len(enabled) > 0:
        enabled_set = set(enabled)
        return [p for p in plugins if p.manifest.name in enabled_set and p.manifest.name not in disabled_set]
    return [p for p in plugins if p.manifest.name not in disabled_set]
