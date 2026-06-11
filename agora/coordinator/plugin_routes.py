"""Plugin management REST API routes (Phase 11.1c).

Provides endpoints for listing, inspecting, and controlling plugins.
Requires admin:full RBAC permission.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .plugin import PluginManifest
from .plugin_manager import PluginCoordinator
from .rbac import Permission, Role, get_current_role, requires

logger = logging.getLogger(__name__)

router = APIRouter()

_plugin_coord: Optional[PluginCoordinator] = None


def init_plugin_route_deps(coord: PluginCoordinator) -> None:
    """Initialize plugin route dependencies. Called at app startup."""
    global _plugin_coord
    _plugin_coord = coord


def _get_coord() -> PluginCoordinator:
    if _plugin_coord is None:
        raise HTTPException(status_code=503, detail="Plugin coordinator not initialized")
    return _plugin_coord


@router.get("/admin/plugins", response_model=list[PluginManifest])
@requires(Permission.ADMIN_FULL)
async def list_plugins(
    _rbac_role: Role | None = Depends(get_current_role),
) -> list[PluginManifest]:
    """List all loaded plugins."""
    coord = _get_coord()
    return coord.list_plugins()


@router.get("/admin/plugins/available", response_model=list[PluginManifest])
@requires(Permission.ADMIN_FULL)
async def list_available_plugins(
    _rbac_role: Role | None = Depends(get_current_role),
) -> list[PluginManifest]:
    """List discoverable but not-yet-loaded plugins."""
    coord = _get_coord()
    return coord.list_available_plugins()


@router.get("/admin/plugins/{name}", response_model=PluginManifest)
@requires(Permission.ADMIN_FULL)
async def get_plugin_detail(
    name: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> PluginManifest:
    """Get detail for a specific loaded plugin."""
    coord = _get_coord()
    plugin = coord.get_plugin(name)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return plugin.manifest
