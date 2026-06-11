"""Auth helpers — Phase 11.2a: Dashboard user credential management.

Parses AGORA_DASHBOARD_USERS, verifies passwords (bcrypt or fallback).
"""
from __future__ import annotations

import logging

from .config import settings

logger = logging.getLogger(__name__)


def parse_dashboard_users() -> dict[str, str]:
    """Parse AGORA_DASHBOARD_USERS into {username: hashed_password}."""
    raw = settings.dashboard_users
    if not raw:
        return {}
    result: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        username, hashed = entry.split(":", 1)
        result[username.strip()] = hashed.strip()
    return result


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hashed version.

    Tries bcrypt if available, falls back to plain-text compare.
    """
    try:
        import bcrypt  # type: ignore
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ImportError:
        logger.warning("bcrypt not installed; using plain-text compare")
        return plain == hashed
