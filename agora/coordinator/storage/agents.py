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
    model: str,
    hermes_endpoint: str = "",
    capabilities: list[str] | None = None,
    role: str = "expert",
) -> dict:
    """Register a new agent. Returns dict with agent_id and registered_at."""
    caps_json = json.dumps(capabilities or [])
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO agents
           (agent_id, name, hermes_endpoint, model,
            capabilities, role, registered_at, is_online)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
        [agent_id, name, hermes_endpoint, model, caps_json, role, now],
    )
    await db.commit()
    return {
        "agent_id": agent_id,
        "name": name,
        "hermes_endpoint": hermes_endpoint,
        "model": model,
        "capabilities": capabilities or [],
        "role": role,
        "registered_at": now,
        "is_online": True,
        "last_seen": None,
    }


async def get_agent(
    db: aiosqlite.Connection, agent_id: str
) -> Optional[dict]:
    """Get agent info by ID, or None if not found."""
    async with db.execute(
        "SELECT * FROM agents WHERE agent_id = ?", [agent_id]
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_agents(
    db: aiosqlite.Connection, online_only: bool = False
) -> list[dict]:
    """List agents, optionally filtered to online only."""
    query = "SELECT * FROM agents"
    params: list = []
    if online_only:
        query += " WHERE is_online = 1"
    async with db.execute(query, params) as cursor:
        return [dict(row) async for row in cursor]


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
    """Remove an agent from the system."""
    await db.execute(
        "DELETE FROM agents WHERE agent_id = ?", [agent_id]
    )
    await db.commit()
