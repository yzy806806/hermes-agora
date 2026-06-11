"""Auth router — Phase 11.2a: Dashboard user login.

POST /api/v1/auth/login validates username+password against
AGORA_DASHBOARD_USERS env var, returns JWT on success.
Returns 501 if AGORA_DASHBOARD_USERS not configured (backward compat).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .auth_helpers import parse_dashboard_users, verify_password
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_token_mgr: Optional[TokenManager] = None


def init_auth_deps(token_mgr: TokenManager) -> None:
    """Set TokenManager reference. Called at app startup."""
    global _token_mgr
    _token_mgr = token_mgr


class LoginRequest(BaseModel):
    """Dashboard login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Dashboard login response."""
    token: str
    role: str
    expires_in: int = 3600


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate dashboard user, return JWT."""
    if _token_mgr is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    users = parse_dashboard_users()
    if not users:
        raise HTTPException(
            status_code=501,
            detail="Dashboard auth not configured (AGORA_DASHBOARD_USERS)",
        )
    hashed = users.get(request.username)
    if hashed is None or not verify_password(request.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # First user is admin, others are observer by default
    role = "admin" if request.username == list(users.keys())[0] else "observer"
    token = _token_mgr.create_token(
        agent_id=f"dashboard_user:{request.username}",
        role=role,
    )
    return LoginResponse(token=token, role=role)
