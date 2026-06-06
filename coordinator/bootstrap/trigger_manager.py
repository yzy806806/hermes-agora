"""Trigger Manager — detect when to start a bootstrap discussion."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import aiosqlite

from .trigger_types import TriggerEvent, TriggerType

logger = logging.getLogger(__name__)


class TriggerManager:
    """Manage bootstrap triggers: create, list, mark processed."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def create_trigger(
        self, trigger_type: TriggerType, topic: str,
        source: str, context: str, priority: int = 0,
    ) -> str:
        """Create a new trigger event. Returns the trigger id."""
        event = TriggerEvent(
            trigger_type=trigger_type, topic=topic,
            source=source, context=context, priority=priority,
        )
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO bootstrap_triggers
                   (trigger_type, topic, source, context,
                    priority, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
                (event.trigger_type.value, event.topic, event.source,
                 event.context, event.priority,
                 event.created_at.isoformat()),
            )
            await db.commit()
            return str(cursor.lastrowid)

    async def get_pending_triggers(self, limit: int = 10) -> list[dict]:
        """Return pending triggers ordered by priority desc, then created_at asc."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM bootstrap_triggers
                   WHERE status = 'pending'
                   ORDER BY priority DESC, created_at ASC LIMIT ?""",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_trigger(self, trigger_id: str) -> Optional[dict]:
        """Get a single trigger by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bootstrap_triggers WHERE id = ?",
                (trigger_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def mark_processed(self, trigger_id: str) -> None:
        """Mark a trigger as processed."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE bootstrap_triggers
                   SET status = 'processed', processed_at = ?
                   WHERE id = ?""",
                (now, trigger_id),
            )
            await db.commit()

    async def mark_failed(self, trigger_id: str) -> None:
        """Mark a trigger as failed."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE bootstrap_triggers
                   SET status = 'failed', processed_at = ?
                   WHERE id = ?""",
                (now, trigger_id),
            )
            await db.commit()
