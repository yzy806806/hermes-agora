"""Assessment CRUD operations for the Agora Coordinator storage layer."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def save_assessment(
    db: aiosqlite.Connection,
    motion_id: str,
    round_num: int,
    result: str,
    consensus_level: str,
    metrics: dict,
    rationale: str,
) -> int:
    """Save an assessment record. Returns the auto-generated id."""
    now = datetime.utcnow().isoformat()
    metrics_json = json.dumps(metrics)
    await db.execute(
        """INSERT INTO assessments
           (motion_id, round, result, consensus_level, metrics,
            rationale, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [motion_id, round_num, result, consensus_level,
         metrics_json, rationale, now],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cursor:
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_latest_assessment(
    db: aiosqlite.Connection,
    motion_id: str,
) -> Optional[dict]:
    """Get the most recent assessment for a motion."""
    async with db.execute(
        """SELECT * FROM assessments
           WHERE motion_id = ?
           ORDER BY created_at DESC LIMIT 1""",
        [motion_id],
    ) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        data = dict(row)
        # Parse metrics JSON
        if data.get("metrics"):
            try:
                data["metrics"] = json.loads(data["metrics"])
            except (json.JSONDecodeError, TypeError):
                pass
        return data


async def get_assessments(
    db: aiosqlite.Connection,
    motion_id: str,
) -> list[dict]:
    """Get all assessments for a motion, ordered by time."""
    async with db.execute(
        """SELECT * FROM assessments
           WHERE motion_id = ?
           ORDER BY created_at""",
        [motion_id],
    ) as cursor:
        results = []
        async for row in cursor:
            data = dict(row)
            if data.get("metrics"):
                try:
                    data["metrics"] = json.loads(data["metrics"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(data)
        return results
