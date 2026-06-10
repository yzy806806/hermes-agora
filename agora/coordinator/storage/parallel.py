"""CRUD for execution_slots and resource_locks (Phase 10)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from ..task_models import ExecutionSlot, ResourceLock

logger = logging.getLogger(__name__)


# --- ExecutionSlot CRUD ---


async def create_execution_slot(
    db: aiosqlite.Connection, slot: ExecutionSlot,
) -> dict:
    """Insert a new execution slot row."""
    await db.execute(
        """INSERT INTO execution_slots
        (task_id, agent_id, started_at, status)
        VALUES (?, ?, ?, ?)""",
        [slot.task_id, slot.agent_id,
         slot.started_at.isoformat(), slot.status],
    )
    await db.commit()
    return slot.model_dump(mode="json")


async def get_execution_slots(
    db: aiosqlite.Connection,
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """List execution slots with optional filters."""
    conds, params = [], []
    if agent_id:
        conds.append("agent_id = ?"); params.append(agent_id)
    if status:
        conds.append("status = ?"); params.append(status)
    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    sql = f"SELECT * FROM execution_slots{where}"
    async with db.execute(sql, params) as cur:
        return [_decode_slot(r) async for r in cur]


async def update_slot_status(
    db: aiosqlite.Connection, task_id: str, status: str,
) -> None:
    """Update execution slot status."""
    await db.execute(
        "UPDATE execution_slots SET status = ? WHERE task_id = ?",
        [status, task_id],
    )
    await db.commit()


async def delete_execution_slot(
    db: aiosqlite.Connection, task_id: str,
) -> None:
    """Remove an execution slot by task_id."""
    await db.execute(
        "DELETE FROM execution_slots WHERE task_id = ?", [task_id],
    )
    await db.commit()


def _decode_slot(row: aiosqlite.Row) -> dict:
    """Decode an execution_slots row into a dict."""
    d = dict(row)
    return d


# --- ResourceLock CRUD ---


async def acquire_resource_lock(
    db: aiosqlite.Connection, lock: ResourceLock,
) -> dict:
    """Insert a new resource lock row."""
    await db.execute(
        """INSERT INTO resource_locks
        (resource_path, locked_by, waiting_tasks, lock_type, acquired_at)
        VALUES (?, ?, ?, ?, ?)""",
        [lock.resource_path, lock.locked_by,
         json.dumps(lock.waiting_tasks), lock.lock_type,
         lock.acquired_at.isoformat()],
    )
    await db.commit()
    return lock.model_dump(mode="json")


async def get_resource_lock(
    db: aiosqlite.Connection, resource_path: str,
) -> Optional[dict]:
    """Get a resource lock by path."""
    async with db.execute(
        "SELECT * FROM resource_locks WHERE resource_path = ?",
        [resource_path],
    ) as cur:
        row = await cur.fetchone()
    return _decode_lock(row) if row else None


async def get_locks_by_task(
    db: aiosqlite.Connection, task_id: str,
) -> list[dict]:
    """Get all locks held by a task."""
    async with db.execute(
        "SELECT * FROM resource_locks WHERE locked_by = ?",
        [task_id],
    ) as cur:
        return [_decode_lock(r) async for r in cur]


async def add_waiting_task(
    db: aiosqlite.Connection, resource_path: str, task_id: str,
) -> None:
    """Add a task to the waiting list of a resource lock."""
    lock = await get_resource_lock(db, resource_path)
    if not lock:
        return
    waiting = lock.get("waiting_tasks", [])
    if task_id not in waiting:
        waiting.append(task_id)
    await db.execute(
        "UPDATE resource_locks SET waiting_tasks = ? WHERE resource_path = ?",
        [json.dumps(waiting), resource_path],
    )
    await db.commit()


async def release_resource_lock(
    db: aiosqlite.Connection, resource_path: str,
) -> None:
    """Remove a resource lock by path."""
    await db.execute(
        "DELETE FROM resource_locks WHERE resource_path = ?",
        [resource_path],
    )
    await db.commit()


async def release_all_locks_for_task(
    db: aiosqlite.Connection, task_id: str,
) -> None:
    """Release all resource locks held by a task."""
    await db.execute(
        "DELETE FROM resource_locks WHERE locked_by = ?", [task_id],
    )
    await db.commit()


def _decode_lock(row: aiosqlite.Row) -> dict:
    """Decode a resource_locks row into a dict."""
    d = dict(row)
    val = d.get("waiting_tasks")
    if isinstance(val, str):
        d["waiting_tasks"] = json.loads(val)
    return d
