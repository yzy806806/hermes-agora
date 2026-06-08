"""Motion CRUD operations for the Agora Coordinator storage layer."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# Keys that may be NULL in DB but need to be [] for Pydantic
_LIST_KEYS = ("action_items", "focus_areas")


def _normalize_motion(data: dict) -> dict:
    """Replace NULL list fields with empty lists for Pydantic."""
    for key in _LIST_KEYS:
        if key in data and data[key] is None:
            data[key] = []
    return data


async def create_motion(
    db: aiosqlite.Connection,
    title: str,
    description: str,
    rounds: int = 3,
    voting_method: str = "simple_majority",
    context: str = "",
) -> dict:
    """Create a new motion. Returns full motion dict."""
    motion_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO motions
           (id, title, description, context, rounds, voting_method,
            status, current_round, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 'draft', 0, ?, ?)""",
        [motion_id, title, description, context, rounds, voting_method, now, now],
    )
    await db.commit()
    async with db.execute(
        "SELECT * FROM motions WHERE id = ?", [motion_id]
    ) as cursor:
        row = await cursor.fetchone()
        return _normalize_motion(dict(row)) if row else {"id": motion_id}


async def get_motion(
    db: aiosqlite.Connection, motion_id: str
) -> Optional[dict]:
    """Get motion by ID, or None if not found."""
    async with db.execute(
        "SELECT * FROM motions WHERE id = ?", [motion_id]
    ) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        return _normalize_motion(dict(row))


async def list_motions(
    db: aiosqlite.Connection,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List motions, optionally filtered by status."""
    query = "SELECT * FROM motions"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    async with db.execute(query, params) as cursor:
        return [_normalize_motion(dict(r)) async for r in cursor]


async def update_motion_status(
    db: aiosqlite.Connection,
    motion_id: str,
    status: str,
    decision: Optional[str] = None,
    rationale: Optional[str] = None,
    action_items: Optional[list[str]] = None,
) -> None:
    """Update motion status and optional fields."""
    now = datetime.now(timezone.utc).isoformat()
    updates = ["status = ?", "updated_at = ?"]
    params: list = [status, now]
    if decision is not None:
        updates.append("decision = ?")
        params.append(decision)
    if rationale is not None:
        updates.append("rationale = ?")
        params.append(rationale)
    if action_items is not None:
        updates.append("action_items = ?")
        params.append(json.dumps(action_items))
    if status == "closed":
        updates.append("closed_at = ?")
        params.append(now)
    params.append(motion_id)
    await db.execute(
        f"UPDATE motions SET {', '.join(updates)} WHERE id = ?", params
    )
    await db.commit()


async def increment_round(
    db: aiosqlite.Connection, motion_id: str
) -> int:
    """Increment motion round. Returns new round number."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE motions SET current_round = current_round + 1, updated_at = ? WHERE id = ?",
        [now, motion_id],
    )
    await db.commit()
    async with db.execute(
        "SELECT current_round FROM motions WHERE id = ?", [motion_id]
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0
