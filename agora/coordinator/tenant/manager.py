"""Tenant CRUD and lifecycle management (Phase 8.2).

Orchestrates tenant creation, listing, retrieval, and deletion
by coordinating GlobalStorage and StorageManager.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from ..storage.global_store import GlobalStorage
from ..storage.storage_manager import StorageManager
from .models import Tenant, TenantConfig

logger = logging.getLogger(__name__)

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class TenantManager:
    """High-level tenant CRUD operations."""

    def __init__(self, storage_mgr: StorageManager) -> None:
        self._storage_mgr = storage_mgr
        self._global_db = storage_mgr.global_db

    async def create_tenant(
        self, tenant_id: str, name: str,
        config: Optional[TenantConfig] = None,
    ) -> Tenant:
        """Create a new tenant with validation."""
        if not _TENANT_ID_RE.match(tenant_id):
            raise ValueError(
                f"Invalid tenant_id '{tenant_id}': must be 1-32 lowercase "
                "alphanumeric chars, hyphens, underscores"
            )
        existing = await self._global_db.get_tenant(tenant_id)
        if existing is not None:
            raise ValueError(f"Tenant '{tenant_id}' already exists")

        cfg = config or TenantConfig()
        data = await self._global_db.create_tenant(
            tenant_id, name, cfg.to_dict()
        )
        # Pre-create the tenant's Storage
        await self._storage_mgr.get_tenant_storage(tenant_id)
        logger.info("Tenant created: %s (%s)", tenant_id, name)
        return Tenant.from_dict(data)

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve a tenant by ID."""
        data = await self._global_db.get_tenant(tenant_id)
        return Tenant.from_dict(data) if data else None

    async def list_tenants(self) -> list[Tenant]:
        """List all active tenants."""
        rows = await self._global_db.list_tenants()
        return [Tenant.from_dict(r) for r in rows]

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Soft-delete a tenant. The 'default' tenant cannot be deleted."""
        if tenant_id == "default":
            raise ValueError("Cannot delete the default tenant")
        deleted = await self._global_db.delete_tenant(tenant_id)
        if deleted:
            await self._storage_mgr.remove_tenant_storage(tenant_id)
            logger.info("Tenant deleted: %s", tenant_id)
        return deleted
