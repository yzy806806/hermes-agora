"""Tenant resource limit enforcement (Phase 8.2).

Raises HTTPException(429) when tenant exceeds configured limits.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import HTTPException

from .models import Tenant

if TYPE_CHECKING:
    from ..storage.storage import Storage

logger = logging.getLogger(__name__)


class TenantResourceGuard:
    """Enforces per-tenant resource limits."""

    def __init__(self) -> None:
        pass

    async def check_agent_registration(
        self, tenant: Tenant, storage: Storage,
    ) -> None:
        """Raise 429 if tenant has too many agents."""
        agents = await storage.list_agents()
        if len(agents) >= tenant.config.max_agents:
            raise HTTPException(
                status_code=429,
                detail=f"Tenant '{tenant.tenant_id}' reached max_agents "
                f"limit ({tenant.config.max_agents})",
            )

    async def check_discussion_start(
        self, tenant: Tenant, storage: Storage,
    ) -> None:
        """Raise 429 if tenant has too many concurrent discussions."""
        motions = await storage.list_motions(status="discussing")
        if len(motions) >= tenant.config.max_concurrent_discussions:
            raise HTTPException(
                status_code=429,
                detail=f"Tenant '{tenant.tenant_id}' reached max concurrent "
                f"discussions limit ({tenant.config.max_concurrent_discussions})",
            )

    async def enforce(
        self, tenant: Tenant, resource: str, storage: Storage,
    ) -> None:
        """Enforce limit for a specific resource type.

        Args:
            tenant: The tenant to check.
            resource: One of 'agent_registration', 'discussion_start'.
            storage: The tenant's Storage instance.

        Raises:
            HTTPException(429) if limit exceeded.
        """
        if resource == "agent_registration":
            await self.check_agent_registration(tenant, storage)
        elif resource == "discussion_start":
            await self.check_discussion_start(tenant, storage)
        else:
            logger.warning("Unknown resource type: %s", resource)
