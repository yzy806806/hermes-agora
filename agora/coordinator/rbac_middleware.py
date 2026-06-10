"""RBAC Middleware for Agora Coordinator.

Phase 10.2a: FastAPI/ASGI middleware that extracts the caller's role
from each request and injects it for downstream @requires() checks.

Token resolution order:
1. JWT Bearer token → decode role claim
2. Admin token fallback → Role.ADMIN
3. No token → Role.OBSERVER (read-only)

Only active when AGORA_RBAC_ENFORCE=true.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from starlette.requests import Request
from starlette.responses import Response

from .config import settings
from .rbac import Role, rbac_enforced

logger = logging.getLogger(__name__)

# Header keys injected into request state
_STATE_ROLE = "_rbac_role"


def _resolve_role(request: Request) -> Role:
    """Determine the role from the request's Authorization header."""
    auth: str = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()

    if not token:
        return Role.OBSERVER

    # Admin token fallback: matches AGORA_ADMIN_TOKEN → ADMIN
    admin_token = settings.admin_token
    if admin_token and token == admin_token:
        return Role.ADMIN

    # TODO (Phase 10.2b): JWT decode → extract role claim
    # For now, agent tokens (ag-*) get AGENT role
    if token.startswith("ag-"):
        return Role.AGENT

    return Role.OBSERVER


class RBACMiddleware:
    """ASGI middleware that resolves and injects the caller's role."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self, scope: dict[str, Any], receive: Callable, send: Callable,
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        if rbac_enforced():
            request = Request(scope, receive)
            role = _resolve_role(request)
            # Write to scope["state"] dict so Starlette builds
            # request.state._rbac_role for downstream Depends.
            scope.setdefault("state", {})
            scope["state"][_STATE_ROLE] = role
            logger.debug(
                "RBAC: resolved role=%s for %s",
                role.value, request.url.path,
            )

        await self.app(scope, receive, send)
