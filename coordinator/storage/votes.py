"""Vote CRUD operations and statistics for the Agora Coordinator storage layer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def add_vote(
    db: aiosqlite.Connection,
    motion_id: str,
    agent_id: str,
    vote: str,
    confidence: float = 1.0,
    reason: Optional[str] = None,
) -> int:
    """Add a vote. Returns the auto-generated vote id."""
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO votes
           (motion_id, agent_id, vote, confidence, reason, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [motion_id, agent_id, vote, confidence, reason, now],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_votes(
    db: aiosqlite.Connection, motion_id: str
) -> list[dict]:
    """Get all votes for a motion, ordered by timestamp."""
    async with db.execute(
        "SELECT * FROM votes WHERE motion_id = ? ORDER BY timestamp",
        [motion_id],
    ) as cursor:
        return [dict(row) async for row in cursor]


async def has_voted(
    db: aiosqlite.Connection, motion_id: str, agent_id: str
) -> bool:
    """Check whether an agent has already voted on a motion."""
    async with db.execute(
        "SELECT 1 FROM votes WHERE motion_id = ? AND agent_id = ?",
        [motion_id, agent_id],
    ) as cursor:
        return await cursor.fetchone() is not None


async def count_votes(
    db: aiosqlite.Connection, motion_id: str
) -> dict[str, int]:
    """Count votes by choice for a motion. Returns {vote: count}."""
    async with db.execute(
        "SELECT vote, COUNT(*) as count FROM votes WHERE motion_id = ? GROUP BY vote",
        [motion_id],
    ) as cursor:
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}


async def get_vote_summary(
    db: aiosqlite.Connection, motion_id: str
) -> dict:
    """Get vote summary with counts per choice."""
    votes = await get_votes(db, motion_id)
    summary: dict = {"yes": 0, "no": 0, "abstain": 0, "total": len(votes)}
    for v in votes:
        choice = v["vote"]
        if choice in summary:
            summary[choice] += 1
    return summary


async def get_active_motion_count(
    db: aiosqlite.Connection,
) -> int:
    """Count motions in draft/discussing/voting status."""
    async with db.execute(
        "SELECT COUNT(*) FROM motions WHERE status IN ('draft','discussing','voting')"
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_participant_count(
    db: aiosqlite.Connection,
) -> int:
    """Count online agents."""
    async with db.execute(
        "SELECT COUNT(*) FROM agents WHERE is_online = 1"
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0
