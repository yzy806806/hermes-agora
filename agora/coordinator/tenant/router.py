"""Tenant API routes (Phase 8.2).

Provides REST endpoints for tenant CRUD:
  POST   /api/v1/tenants          - Create tenant
  GET    /api/v1/tenants          - List tenants
  GET    /api/v1/tenants/{tid}    - Get tenant
  DELETE /api/v1/tenants/{tid}    - Delete tenant
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .models import Tenant, TenantConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenants", tags=["tenants"])

# Module-level singleton — set by main.py during app startup
_tenant_manager = None


class TenantCreateRequest(BaseModel):
    """Request body for creating a tenant."""

    tenant_id: str = Field(
        ...,
        pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$",
        description="Unique slug, 1-32 lowercase alphanumeric/hyphen/underscore",
    )
    name: str = Field(..., min_length=1, max_length=100)
    config: Optional[TenantConfig] = None


class TenantResponse(BaseModel):
    """Response model for a tenant."""

    tenant_id: str
    name: str
    created_at: str
    config: dict


def init_tenant_deps(tenant_manager) -> None:
    """Set the TenantManager singleton. Called once at startup."""
    global _tenant_manager
    _tenant_manager = tenant_manager


def _get_tm():
    if _tenant_manager is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _tenant_manager


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(request: TenantCreateRequest) -> TenantResponse:
    """Create a new tenant."""
    tm = _get_tm()
    try:
        tenant = await tm.create_tenant(
            request.tenant_id, request.name, request.config
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _tenant_to_response(tenant)


@router.get("", response_model=list[TenantResponse])
async def list_tenants() -> list[TenantResponse]:
    """List all active tenants."""
    tm = _get_tm()
    tenants = await tm.list_tenants()
    return [_tenant_to_response(t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str) -> TenantResponse:
    """Get a specific tenant by ID."""
    tm = _get_tm()
    tenant = await tm.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_to_response(tenant)


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str) -> dict:
    """Soft-delete a tenant (cannot delete 'default')."""
    tm = _get_tm()
    try:
        deleted = await tm.delete_tenant(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"status": "deleted", "tenant_id": tenant_id}


def _tenant_to_response(t: Tenant) -> TenantResponse:
    return TenantResponse(
        tenant_id=t.tenant_id,
        name=t.name,
        created_at=t.created_at.isoformat(),
        config=t.config.to_dict(),
    )
