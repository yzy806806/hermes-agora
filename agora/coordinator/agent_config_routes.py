"""Agent config and token rotation REST endpoints.

Phase 11.1b: PUT /admin/agents/{agent_id}/config
             POST /admin/agents/{agent_id}/token
"""
from __future__ import annotations

import json
import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from .models import (
    AgentConfigResponse,
    AgentConfigUpdate,
    TokenRotateResponse,
)
from .rbac import Permission, Role, get_current_role, requires
from .storage import Storage
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter()

_storage: Optional[Storage] = None
_token_mgr: Optional[TokenManager] = None


def init_agent_config_deps(
    storage: Storage, token_mgr: TokenManager,
) -> None:
    """Wire storage and token manager. Called at app startup."""
    global _storage, _token_mgr
    _storage = storage
    _token_mgr = token_mgr


def _get_storage() -> Storage:
    if _storage is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    return _storage


def _get_token_mgr() -> TokenManager:
    if _token_mgr is None:
        raise HTTPException(status_code=503, detail="Not initialized")
    return _token_mgr


@router.put("/admin/agents/{agent_id}/config",
            response_model=AgentConfigResponse)
@requires(Permission.ADMIN_FULL)
async def update_agent_config(
    agent_id: str,
    body: AgentConfigUpdate,
    _rbac_role: Role | None = Depends(get_current_role),
) -> AgentConfigResponse:
    """Update agent config (TPM, concurrency, roles). Admin only."""
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.update_agent_config(
        agent_id,
        tpm_limit=body.tpm_limit,
        tpm_burst_factor=body.tpm_burst_factor,
        max_concurrent_tasks=body.max_concurrent_tasks,
        role=body.role,
        allowed_discussion_roles=body.allowed_discussion_roles,
    )
    updated = await storage.get_agent(agent_id)
    roles_raw = updated.get("allowed_discussion_roles", '["participant"]')
    roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
    return AgentConfigResponse(
        agent_id=agent_id,
        tpm_limit=updated.get("tpm_limit", 10000),
        tpm_burst_factor=updated.get("tpm_burst_factor", 1.5),
        max_concurrent_tasks=updated.get("max_concurrent_tasks", 2),
        role=updated.get("role", "participant"),
        allowed_discussion_roles=roles,
    )


@router.post("/admin/agents/{agent_id}/token",
             response_model=TokenRotateResponse)
@requires(Permission.ADMIN_FULL)
async def rotate_agent_token(
    agent_id: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> TokenRotateResponse:
    """Rotate agent token. Admin only."""
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    new_token = f"ag-{secrets.token_hex(16)}"
    await storage.update_agent_token(agent_id, new_token)
    return TokenRotateResponse(
        agent_id=agent_id, agent_token=new_token,
    )
