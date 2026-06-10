"""RBAC storage: CRUD for roles, tokens, and audit_log tables."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from .schema import DEFAULT_ROLES

logger = logging.getLogger(__name__)


# --- Role CRUD ---

async def seed_default_roles(db: aiosqlite.Connection) -> None:
    """Insert default roles (admin, agent, observer) if not present."""
    now = datetime.now(timezone.utc).isoformat()
    for name, perms in DEFAULT_ROLES.items():
        await db.execute(
            "INSERT OR IGNORE INTO roles (name, permissions_json, created_at) "
            "VALUES (?, ?, ?)",
            [name, json.dumps(perms), now],
        )
    await db.commit()
    logger.info("Seeded default RBAC roles")


async def get_role(db: aiosqlite.Connection, name: str) -> Optional[dict]:
    """Look up a role by name. Returns dict or None."""
    async with db.execute(
        "SELECT id, name, permissions_json, created_at FROM roles WHERE name = ?",
        [name],
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    return {
        "id": row["id"], "name": row["name"],
        "permissions": json.loads(row["permissions_json"]),
        "created_at": row["created_at"],
    }


async def list_roles(db: aiosqlite.Connection) -> list[dict]:
    """Return all roles."""
    async with db.execute(
        "SELECT id, name, permissions_json, created_at FROM roles"
    ) as cur:
        rows = await cur.fetchall()
    return [
        {"id": r["id"], "name": r["name"],
         "permissions": json.loads(r["permissions_json"]),
         "created_at": r["created_at"]}
        for r in rows
    ]


# --- Token CRUD ---

async def create_token(
    db: aiosqlite.Connection, principal_id: str, role: str,
    token_hash: str, token_id: str,
    scopes: list[str] | None = None,
    expires_at: Optional[str] = None,
    tenant_id: str = "default",
) -> dict:
    """Insert a new token record."""
    now = datetime.now(timezone.utc).isoformat()
    scopes_json = json.dumps(scopes or [])
    await db.execute(
        "INSERT INTO tokens (token_id, token_hash, principal_id, role, "
        "scopes, tenant_id, expires_at, is_revoked, revoked_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)",
        [token_id, token_hash, principal_id, role,
         scopes_json, tenant_id, expires_at, now],
    )
    await db.commit()
    return {"token_id": token_id, "principal_id": principal_id,
            "role": role, "scopes": scopes or [],
            "token_hash": token_hash, "expires_at": expires_at,
            "created_at": now, "tenant_id": tenant_id}


async def get_token_by_hash(
    db: aiosqlite.Connection, token_hash: str,
) -> Optional[dict]:
    """Look up a non-revoked token by its hash."""
    async with db.execute(
        "SELECT * FROM tokens WHERE token_hash = ? "
        "AND is_revoked = 0", [token_hash],
    ) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if "scopes" in d and isinstance(d["scopes"], str):
        d["scopes"] = json.loads(d["scopes"])
    return d


async def revoke_token(db: aiosqlite.Connection, token_id: int) -> None:
    """Revoke a token by row id."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE tokens SET is_revoked = 1, revoked_at = ? "
        "WHERE id = ?", [now, token_id])
    await db.commit()


# --- Audit Log CRUD ---

async def log_audit(
    db: aiosqlite.Connection, event_type: str, actor_id: str,
    action: str, resource: Optional[str] = None,
    actor_role: Optional[str] = None,
    details: Optional[dict] = None, tenant_id: str = "default",
) -> int:
    """Write an audit event."""
    now = datetime.now(timezone.utc).isoformat()
    async with db.execute(
        "INSERT INTO audit_log (event_type, actor_id, actor_role, action, "
        "resource, details_json, timestamp, tenant_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [event_type, actor_id, actor_role, action, resource,
         json.dumps(details) if details else None, now, tenant_id],
    ) as cur:
        audit_id: int = cur.lastrowid  # type: ignore[assignment]
    await db.commit()
    return audit_id


async def query_audit(
    db: aiosqlite.Connection, tenant_id: str = "default",
    actor_id: Optional[str] = None, event_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Query audit log with optional filters."""
    clauses = ["tenant_id = ?"]
    params: list = [tenant_id]
    if actor_id:
        clauses.append("actor_id = ?")
        params.append(actor_id)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    params.append(limit)
    sql = ("SELECT id, event_type, actor_id, actor_role, action, "
           "resource, details_json, timestamp, tenant_id "
           "FROM audit_log WHERE " + " AND ".join(clauses)
           + " ORDER BY timestamp DESC LIMIT ?")
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]
