"""Bootstrap trigger & schedule CRUD for the Agora storage layer."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import aiosqlite


async def create_trigger(
    db: aiosqlite.Connection, trigger_type: str, topic: str,
    source: str, context: str, priority: int = 0,
) -> int:
    """Insert a bootstrap trigger. Returns auto-generated id."""
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO bootstrap_triggers
           (trigger_type, topic, source, context,
            priority, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
        [trigger_type, topic, source, context, priority, now],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_pending_triggers(
    db: aiosqlite.Connection, limit: int = 10,
) -> list[dict]:
    """Return pending triggers ordered by priority desc, time asc."""
    async with db.execute(
        """SELECT * FROM bootstrap_triggers
           WHERE status = 'pending'
           ORDER BY priority DESC, created_at ASC LIMIT ?""",
        [limit],
    ) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_trigger_status(
    db: aiosqlite.Connection, trigger_id: int,
    status: str,
) -> None:
    """Update trigger status and set processed_at."""
    now = datetime.utcnow().isoformat()
    await db.execute(
        """UPDATE bootstrap_triggers
           SET status = ?, processed_at = ? WHERE id = ?""",
        [status, now, trigger_id],
    )
    await db.commit()


async def create_schedule(
    db: aiosqlite.Connection, name: str,
    cron_expression: str, topic_template: str,
    next_run: Optional[str] = None,
) -> int:
    """Insert a bootstrap schedule. Returns auto-generated id."""
    await db.execute(
        """INSERT INTO bootstrap_schedules
           (name, cron_expression, topic_template, next_run)
           VALUES (?, ?, ?, ?)""",
        [name, cron_expression, topic_template, next_run],
    )
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_schedules(
    db: aiosqlite.Connection, enabled_only: bool = False,
) -> list[dict]:
    """Return schedules, optionally filtered to enabled only."""
    sql = "SELECT * FROM bootstrap_schedules"
    params: list = []
    if enabled_only:
        sql += " WHERE enabled = 1"
    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
