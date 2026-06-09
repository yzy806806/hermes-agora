"""Bootstrap approval & agent CRUD for the Agora storage layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite


async def create_approval(
    db: aiosqlite.Connection, motion_id: str,
    decision: str, rationale: str = "",
    action_items: Optional[list[dict]] = None,
) -> int:
    """Insert an approval request. Returns auto-generated id."""
    now = datetime.now(timezone.utc).isoformat()
    items_json = json.dumps(action_items or [])
    await db.execute(
        """INSERT INTO bootstrap_approvals
           (motion_id, decision, rationale, action_items,
            approval_status, requested_at)
           VALUES (?, ?, ?, ?, 'pending', ?)""",
        [motion_id, decision, rationale, items_json, now],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def decide_approval(
    db: aiosqlite.Connection, approval_id: int,
    approved: bool, approved_by: str = "",
    feedback: str = "",
) -> None:
    """Process an approval decision."""
    status = "approved" if approved else "rejected"
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """UPDATE bootstrap_approvals
           SET approval_status = ?, approved_by = ?,
               feedback = ?, processed_at = ?
           WHERE id = ?""",
        [status, approved_by, feedback, now, approval_id],
    )
    await db.commit()


async def get_pending_approvals(
    db: aiosqlite.Connection, limit: int = 10,
) -> list[dict]:
    """Return pending approvals."""
    async with db.execute(
        """SELECT * FROM bootstrap_approvals
           WHERE approval_status = 'pending'
           ORDER BY requested_at ASC LIMIT ?""",
        [limit],
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def register_bootstrap_agent(
    db: aiosqlite.Connection, agent_id: str,
    name: str, role: str, model: str = "",
    capabilities: Optional[list[str]] = None,
) -> int:
    """Register a bootstrap agent. Returns auto-generated id."""
    caps_json = json.dumps(capabilities or [])
    await db.execute(
        """INSERT OR REPLACE INTO bootstrap_agents
           (agent_id, name, role, model, capabilities)
           VALUES (?, ?, ?, ?, ?)""",
        [agent_id, name, role, model, caps_json],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_bootstrap_agents(
    db: aiosqlite.Connection, active_only: bool = False,
) -> list[dict]:
    """Return bootstrap agents, optionally filtered to active."""
    sql = "SELECT * FROM bootstrap_agents"
    params: list = []
    if active_only:
        sql += " WHERE active = 1"
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
