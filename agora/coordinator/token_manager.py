"""JWT token management for Agora RBAC (Phase 10.2b).

Provides TokenManager for creating, validating, rotating, and revoking
JWT tokens. Blocklist is in-memory with periodic cleanup.
Backward compat: AGORA_ADMIN_TOKEN still works as fallback.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_SECONDS = 3600  # 1 hour
BLOCKLIST_CLEANUP_INTERVAL = 300  # 5 minutes


class TokenPayload:
    """Decoded JWT payload data."""

    __slots__ = ("agent_id", "role", "tenant_id", "exp", "iat", "jti")

    def __init__(
        self, agent_id: str, role: str,
        tenant_id: str | None = None,
        exp: int = 0, iat: int = 0, jti: str = "",
    ):
        self.agent_id = agent_id
        self.role = role
        self.tenant_id = tenant_id
        self.exp = exp
        self.iat = iat
        self.jti = jti


class TokenManager:
    """Create, validate, rotate, and revoke JWT access tokens."""

    def __init__(self, secret: str | None = None) -> None:
        self._secret = secret or os.environ.get(
            "AGORA_JWT_SECRET", ""
        )
        if not self._secret:
            self._secret = secrets.token_hex(32)
            logger.warning(
                "AGORA_JWT_SECRET not set; generated ephemeral secret. "
                "Tokens will not survive restarts."
            )
        self._blocklist: dict[str, int] = {}  # jti -> exp timestamp
        self._last_cleanup = time.monotonic()

    def create_token(
        self, agent_id: str, role: str,
        tenant_id: str | None = None,
        expires_delta: int | None = None,
    ) -> str:
        """Create a signed JWT with agent_id, role, tenant_id claims."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(
            seconds=expires_delta or DEFAULT_EXPIRY_SECONDS
        )
        payload = {
            "agent_id": agent_id,
            "role": role,
            "tenant_id": tenant_id,
            "exp": expiry,
            "iat": now,
            "jti": secrets.token_hex(8),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def validate_token(self, token: str) -> TokenPayload:
        """Verify signature, check expiry, check blocklist.

        Raises ValueError on invalid/expired/revoked tokens.
        """
        self._maybe_cleanup()
        try:
            data = jwt.decode(
                token, self._secret, algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}") from exc
        jti = data.get("jti", "")
        if jti in self._blocklist:
            raise ValueError("Token has been revoked")
        return TokenPayload(
            agent_id=data["agent_id"],
            role=data["role"],
            tenant_id=data.get("tenant_id"),
            exp=data.get("exp", 0),
            iat=data.get("iat", 0),
            jti=jti,
        )

    def revoke_token(self, token: str) -> None:
        """Add token JTI to the in-memory blocklist."""
        try:
            data = jwt.decode(
                token, self._secret, algorithms=["HS256"],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError:
            logger.warning("Attempted to revoke an invalid token")
            return
        jti = data.get("jti", "")
        exp = data.get("exp", 0)
        if jti:
            self._blocklist[jti] = exp

    def rotate_token(self, old_token: str) -> str:
        """Revoke old token, issue new one with same claims."""
        try:
            data = jwt.decode(
                old_token, self._secret, algorithms=["HS256"],
                options={"verify_exp": False},
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Cannot rotate invalid token: {exc}") from exc
        jti = data.get("jti", "")
        exp = data.get("exp", 0)
        if jti:
            self._blocklist[jti] = exp
        return self.create_token(
            agent_id=data["agent_id"],
            role=data["role"],
            tenant_id=data.get("tenant_id"),
        )

    def _maybe_cleanup(self) -> None:
        """Periodically remove expired JTIs from blocklist."""
        now = time.monotonic()
        if now - self._last_cleanup < BLOCKLIST_CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        cutoff = int(time.time())
        expired = [
            jti for jti, exp in self._blocklist.items()
            if exp and exp < cutoff
        ]
        for jti in expired:
            del self._blocklist[jti]
        if expired:
            logger.debug(
                "Blocklist cleanup: removed %d expired entries", len(expired))
        # Safety valve: clear all if blocklist is still too large
        if len(self._blocklist) > 10000:
            logger.info("Blocklist exceeded 10k entries; clearing")
            self._blocklist.clear()
