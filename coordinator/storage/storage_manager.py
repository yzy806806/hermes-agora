"""Multi-tenant Storage manager (Phase 8.2).

Manages per-tenant Storage instances with lazy creation.
Each tenant gets its own SQLite database under data/tenants/{tid}/agora.db.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .global_store import GlobalStorage
from .storage import Storage

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages multi-tenant Storage instances.

    - global.db holds the tenant registry
    - data/tenants/{tid}/agora.db holds each tenant's data
    - Storage instances are cached in _tenants dict
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.global_db = GlobalStorage(data_dir / "global.db")
        self._tenants: dict[str, Storage] = {}

    async def init(self) -> None:
        """Initialize global DB and ensure the 'default' tenant exists."""
        await self.global_db.init_db()
        existing = await self.global_db.get_tenant("default")
        if existing is None:
            await self.global_db.create_tenant(
                "default", "Default",
                {"max_agents": 100, "max_concurrent_discussions": 50},
            )
            logger.info("Created default tenant")
        # Pre-warm the default tenant Storage
        await self.get_tenant_storage("default")
        logger.info("StorageManager initialized (data_dir=%s)", self.data_dir)

    async def get_tenant_storage(self, tenant_id: str) -> Storage:
        """Get or lazily create a tenant's Storage instance."""
        if tenant_id not in self._tenants:
            db_path = self.data_dir / "tenants" / tenant_id / "agora.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            storage = Storage(str(db_path))
            await storage.init_db()
            self._tenants[tenant_id] = storage
            logger.info("Created Storage for tenant %s", tenant_id)
        return self._tenants[tenant_id]

    def get_cached(self, tenant_id: str) -> Optional[Storage]:
        """Return cached Storage or None (no lazy creation)."""
        return self._tenants.get(tenant_id)

    async def remove_tenant_storage(self, tenant_id: str) -> None:
        """Remove a tenant's cached Storage (does NOT delete files)."""
        self._tenants.pop(tenant_id, None)
        logger.info("Removed Storage cache for tenant %s", tenant_id)
