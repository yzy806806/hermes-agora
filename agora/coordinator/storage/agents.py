"""Agent CRUD operations for the Agora Coordinator storage layer."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def register_agent(
    db: aiosqlite.Connection,
    agent_id: str,
    name: str,
    model: str = "unknown",
    capabilities: list[str] | None = None,
    role: str = "participant",
    agent_type: str = "hermes",
    max_concurrent_tasks: int = 2,
    agent_token: str = "",
    is_approved: bool = False,
    approval_status: str = "pending",
    tpm_limit: int = 10000,
    tpm_burst_factor: float = 1.5,
) -> dict:
    """Register a new agent with Phase 9.3 fields. Returns dict."""
    caps_json = json.dumps(capabilities or [])
    active_tasks_json = json.dumps([])
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO agents
           (agent_id, name, model, capabilities, role,
            agent_type, max_concurrent_tasks, agent_token,
            is_approved, approval_status, load, active_tasks,
            registered_at, is_online, tpm_limit, tpm_burst_factor)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        [agent_id, name, model, caps_json, role,
         agent_type, max_concurrent_tasks, agent_token,
         1 if is_approved else 0, approval_status, 0.0,
         active_tasks_json, now, tpm_limit, tpm_burst_factor],
    )
    await db.commit()
    return {
        "agent_id": agent_id, "name": name, "model": model,
        "capabilities": capabilities or [], "role": role,
        "agent_type": agent_type,
        "max_concurrent_tasks": max_concurrent_tasks,
        "agent_token": agent_token,
        "is_approved": is_approved,
        "approval_status": approval_status,
        "load": 0.0, "active_tasks": [],
        "registered_at": now, "is_online": True,
        "last_seen": None,
        "tpm_limit": tpm_limit,
        "tpm_burst_factor": tpm_burst_factor,
    }


async def get_agent(
    db: aiosqlite.Connection, agent_id: str
) -> Optional[dict]:
    """Get agent info by ID, or None if not found."""
    async with db.execute(
        "SELECT * FROM agents WHERE agent_id = ?", [agent_id]
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        # Normalize is_approved from DB int (0/1) to Python bool
        if "is_approved" in d and isinstance(d["is_approved"], int):
            d["is_approved"] = bool(d["is_approved"])
        # Deserialize JSON fields (capabilities, active_tasks)
        if "capabilities" in d and isinstance(d["capabilities"], str):
            d["capabilities"] = json.loads(d["capabilities"])
        if "active_tasks" in d and isinstance(d["active_tasks"], str):
            d["active_tasks"] = json.loads(d["active_tasks"])
        return d


async def get_agent_by_token(
    db: aiosqlite.Connection, token: str
) -> Optional[dict]:
    """Look up agent by their agent_token (for WS auth)."""
    async with db.execute(
        "SELECT * FROM agents WHERE agent_token = ?", [token]
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        if "is_approved" in d and isinstance(d["is_approved"], int):
            d["is_approved"] = bool(d["is_approved"])
        if "capabilities" in d and isinstance(d["capabilities"], str):
            d["capabilities"] = json.loads(d["capabilities"])
        if "active_tasks" in d and isinstance(d["active_tasks"], str):
            d["active_tasks"] = json.loads(d["active_tasks"])
        return d


async def list_agents(
    db: aiosqlite.Connection, online_only: bool = False
) -> list[dict]:
    """List agents, optionally filtered to online only."""
    query = "SELECT * FROM agents"
    params: list = []
    if online_only:
        query += " WHERE is_online = 1"
    async with db.execute(query, params) as cursor:
        rows = [dict(row) async for row in cursor]
    for d in rows:
        if "is_approved" in d and isinstance(d["is_approved"], int):
            d["is_approved"] = bool(d["is_approved"])
        if "capabilities" in d and isinstance(d["capabilities"], str):
            d["capabilities"] = json.loads(d["capabilities"])
        if "active_tasks" in d and isinstance(d["active_tasks"], str):
            d["active_tasks"] = json.loads(d["active_tasks"])
    return rows


async def set_agent_online(
    db: aiosqlite.Connection, agent_id: str, online: bool
) -> None:
    """Set agent online status and update last_seen_at."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE agents SET is_online = ?, last_seen_at = ? WHERE agent_id = ?",
        [1 if online else 0, now, agent_id],
    )
    await db.commit()


async def deregister_agent(
    db: aiosqlite.Connection, agent_id: str
) -> None:
    """Remove an agent from the system.

    Cleans up dependent rate_limit_usage rows before deleting
    to avoid FOREIGN KEY constraint failures.
    """
    await db.execute(
        "DELETE FROM rate_limit_usage WHERE agent_id = ?",
        [agent_id],
    )
    await db.execute(
        "DELETE FROM agents WHERE agent_id = ?", [agent_id]
    )
    await db.commit()


async def set_agent_approval(
    db: aiosqlite.Connection,
    agent_id: str,
    is_approved: bool,
    approval_status: str,
) -> None:
    """Update agent approval status (Phase 9.3 admin endpoints)."""
    await db.execute(
        "UPDATE agents SET is_approved = ?, approval_status = ? WHERE agent_id = ?",
        [1 if is_approved else 0, approval_status, agent_id],
    )
    await db.commit()


async def update_agent_tpm_config(
    db: aiosqlite.Connection,
    agent_id: str,
    tpm_limit: int | None = None,
    tpm_burst_factor: float | None = None,
) -> None:
    """Update agent TPM config. Only updates provided fields."""
    parts, params = [], []
    if tpm_limit is not None:
        parts.append("tpm_limit = ?")
        params.append(tpm_limit)
    if tpm_burst_factor is not None:
        parts.append("tpm_burst_factor = ?")
        params.append(tpm_burst_factor)
    if not parts:
        return
    params.append(agent_id)
    await db.execute(
        f"UPDATE agents SET {', '.join(parts)} WHERE agent_id = ?",
        params,
    )
    await db.commit()
