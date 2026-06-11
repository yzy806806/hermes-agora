"""Plugin management action routes (Phase 11.1c).

Reload, disable (unload), and enable (load) endpoints.
Requires admin:full RBAC permission.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .plugin_manager import PluginCoordinator
from .rbac import Permission, Role, get_current_role, requires

logger = logging.getLogger(__name__)

router = APIRouter()

_plugin_coord: Optional[PluginCoordinator] = None


def init_plugin_action_deps(coord: PluginCoordinator) -> None:
    """Initialize plugin action route dependencies."""
    global _plugin_coord
    _plugin_coord = coord


def _get_coord() -> PluginCoordinator:
    if _plugin_coord is None:
        raise HTTPException(status_code=503, detail="Plugin coordinator not initialized")
    return _plugin_coord


@router.post("/admin/plugins/{name}/reload")
@requires(Permission.ADMIN_FULL)
async def reload_plugin(
    name: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Reload a loaded plugin (unload then load)."""
    coord = _get_coord()
    if coord.get_plugin(name) is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    await coord.reload_plugin(name)
    return {"status": "reloaded", "name": name}


@router.post("/admin/plugins/{name}/disable")
@requires(Permission.ADMIN_FULL)
async def disable_plugin(
    name: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Disable (unload) a loaded plugin."""
    coord = _get_coord()
    if coord.get_plugin(name) is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    await coord.unload_plugin(name)
    return {"status": "disabled", "name": name}


@router.post("/admin/plugins/{name}/enable")
@requires(Permission.ADMIN_FULL)
async def enable_plugin(
    name: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Enable (load) a discoverable plugin by name."""
    coord = _get_coord()
    available = coord.list_available_plugins()
    match = [p for p in available if p.name == name]
    if not match:
        raise HTTPException(status_code=404, detail="Plugin not available")
    # Re-discover to get the plugin instance
    from .plugin_discovery import discover_plugins
    discovered = discover_plugins()
    plugin = next((p for p in discovered if p.manifest.name == name), None)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin instance not found")
    await coord.load_plugin(plugin)
    return {"status": "enabled", "name": name}
