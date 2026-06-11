"""Plugin Coordinator — manages plugin lifecycle and hooks.

Phase 10.3b: PluginCoordinator class with load, unload,
hook registration, fire-and-forget hook dispatch, and health checks.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from agora.coordinator.plugin import AgoraPlugin, HookContext, HookPoint, PluginManifest
from agora.coordinator.plugin_discovery import discover_plugins, filter_plugins

logger = logging.getLogger(__name__)


class PluginCoordinator:
    """Manages plugin lifecycle and hooks."""

    def __init__(self, storage: Any = None, config: Any = None) -> None:
        self._plugins: dict[str, AgoraPlugin] = {}
        self._hook_registry: dict[HookPoint, list[Callable]] = {
            h: [] for h in HookPoint
        }
        self._storage = storage
        self._config = config

    async def load_plugin(self, plugin: AgoraPlugin) -> None:
        """Validate manifest, call on_load, register hooks."""
        name = plugin.manifest.name
        if name in self._plugins:
            logger.warning("Plugin %s already loaded, skipping", name)
            return
        try:
            await plugin.on_load(self)
        except Exception:
            logger.exception("Plugin %s on_load failed", name)
            return
        for hp in plugin.manifest.hook_points:
            handler = getattr(plugin, f"on_{hp.value.replace('.', '_')}", None)
            if handler:
                self._hook_registry[hp].append(handler)
        self._plugins[name] = plugin
        logger.info("Plugin %s v%s loaded", name, plugin.manifest.version)

    async def unload_plugin(self, name: str) -> None:
        """Call on_unload, remove hooks."""
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            logger.warning("Plugin %s not found for unload", name)
            return
        try:
            await plugin.on_unload()
        except Exception:
            logger.exception("Plugin %s on_unload failed", name)
        for hp in plugin.manifest.hook_points:
            handler = getattr(plugin, f"on_{hp.value.replace('.', '_')}", None)
            if handler:
                try:
                    self._hook_registry[hp].remove(handler)
                except ValueError:
                    pass
        logger.info("Plugin %s unloaded", name)

    async def fire_hook(self, hook_point: HookPoint, ctx: HookContext) -> None:
        """Fire-and-forget to all registered plugins."""
        for handler in list(self._hook_registry.get(hook_point, [])):
            try:
                asyncio.ensure_future(handler(ctx))
            except Exception:
                logger.exception("Hook %s handler failed", hook_point.value)

    async def health_check_all(self) -> dict[str, bool]:
        """Call health_check on all plugins, disable failing ones."""
        results: dict[str, bool] = {}
        for name, plugin in list(self._plugins.items()):
            try:
                ok = await plugin.health_check()
            except Exception:
                ok = False
            results[name] = ok
            if not ok:
                logger.warning("Plugin %s health check failed, unloading", name)
                await self.unload_plugin(name)
        return results

    def get_plugin(self, name: str) -> AgoraPlugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginManifest]:
        """List manifests of all loaded plugins."""
        return [p.manifest for p in self._plugins.values()]

    def register_hook(
        self, plugin: AgoraPlugin, hook: HookPoint, handler: Callable | None = None,
    ) -> None:
        """Register a plugin for a specific hook event."""
        target = handler or getattr(
            plugin, f"on_{hook.value.replace('.', '_')}", None,
        )
        if target is None:
            logger.warning("No handler for hook %s on plugin %s", hook, plugin.manifest.name)
            return
        self._hook_registry[hook].append(target)

    async def reload_plugin(self, name: str) -> None:
        """Unload then re-load a plugin by name."""
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning("Plugin %s not found for reload", name)
            return
        await self.unload_plugin(name)
        await self.load_plugin(plugin)

    def list_available_plugins(self) -> list[PluginManifest]:
        """List manifests of discoverable but not-yet-loaded plugins."""
        discovered = discover_plugins()
        loaded_names = set(self._plugins.keys())
        return [p.manifest for p in discovered if p.manifest.name not in loaded_names]
