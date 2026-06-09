"""Message CRUD operations for the Agora Coordinator storage layer."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def add_message(
    db: aiosqlite.Connection,
    motion_id: str,
    agent_id: str,
    round_num: int,
    stance: str,
    content: str,
    evidence: list[dict] | None = None,
) -> int:
    """Add a message. Returns the auto-generated message id."""
    now = datetime.now(timezone.utc).isoformat()
    evidence_json = json.dumps(evidence or [])
    await db.execute(
        """INSERT INTO messages
           (motion_id, agent_id, round_num, stance, content, evidence, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [motion_id, agent_id, round_num, stance, content, evidence_json, now],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_messages(
    db: aiosqlite.Connection,
    motion_id: str,
    round_num: Optional[int] = None,
    agent_id: Optional[str] = None,
) -> list[dict]:
    """Get messages for a motion, optionally filtered by round/agent."""
    query = "SELECT * FROM messages WHERE motion_id = ?"
    params: list = [motion_id]
    if round_num is not None:
        query += " AND round_num = ?"
        params.append(round_num)
    if agent_id is not None:
        query += " AND agent_id = ?"
        params.append(agent_id)
    query += " ORDER BY timestamp ASC"
    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def count_messages_by_round(
    db: aiosqlite.Connection, motion_id: str, round_num: int
) -> int:
    """Count messages in a specific round of a motion."""
    async with db.execute(
        "SELECT COUNT(*) FROM messages WHERE motion_id = ? AND round_num = ?",
        [motion_id, round_num],
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0
