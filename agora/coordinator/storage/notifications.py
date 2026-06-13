"""Notification CRUD for Phase 13 dashboard enhancement."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def create_notification(
    db: aiosqlite.Connection,
    type: str,
    title: str,
    body: str,
    project_id: str,
    priority: str = "medium",
) -> dict:
    """Insert a new notification. Returns the full record dict."""
    nid = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": nid, "type": type, "title": title, "body": body,
        "project_id": project_id, "priority": priority,
        "created_at": now, "read": 0,
    }
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    await db.execute(
        f"INSERT INTO notifications ({cols}) VALUES ({placeholders})",
        list(row.values()),
    )
    await db.commit()
    return _row_to_dict(row)


async def get_notification(
    db: aiosqlite.Connection, notif_id: str,
) -> Optional[dict]:
    """Get a notification by ID, or None."""
    async with db.execute(
        "SELECT * FROM notifications WHERE id = ?", [notif_id],
    ) as cur:
        row = await cur.fetchone()
    return _row_to_dict(dict(row)) if row else None


async def list_notifications(
    db: aiosqlite.Connection,
    project_id: Optional[str] = None,
    unread_only: bool = False,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List notifications with optional filters."""
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if unread_only:
        clauses.append("read = 0")
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])
    async with db.execute(
        f"SELECT * FROM notifications {where} "
        f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params,
    ) as cur:
        rows = [row async for row in cur]
    return [_row_to_dict(dict(r)) for r in rows]


async def count_notifications(
    db: aiosqlite.Connection,
    project_id: Optional[str] = None,
    unread_only: bool = False,
    priority: Optional[str] = None,
) -> tuple[int, int]:
    """Return (total, unread_count) matching the given filters.

    total counts all rows matching project_id/priority filters.
    unread_count counts only unread rows among those.
    """
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    async with db.execute(
        f"SELECT COUNT(*) FROM notifications {where}", params,
    ) as cur:
        row = await cur.fetchone()
    total = row[0]
    unread_clauses = clauses + ["read = 0"]
    unread_params = list(params)
    unread_where = f"WHERE {' AND '.join(unread_clauses)}"
    async with db.execute(
        f"SELECT COUNT(*) FROM notifications {unread_where}",
        unread_params,
    ) as cur:
        row = await cur.fetchone()
    unread_count = row[0]
    return total, unread_count


async def mark_read(
    db: aiosqlite.Connection, notif_id: str,
) -> Optional[dict]:
    """Mark a single notification as read. Returns updated record."""
    await db.execute(
        "UPDATE notifications SET read = 1 WHERE id = ?", [notif_id],
    )
    await db.commit()
    return await get_notification(db, notif_id)


async def mark_all_read(
    db: aiosqlite.Connection, project_id: Optional[str] = None,
) -> int:
    """Mark all (optionally project-scoped) notifications as read."""
    if project_id is not None:
        cur = await db.execute(
            "UPDATE notifications SET read = 1 WHERE project_id = ?",
            [project_id],
        )
    else:
        cur = await db.execute("UPDATE notifications SET read = 1")
    await db.commit()
    return cur.rowcount


def _row_to_dict(row: dict) -> dict:
    """Convert a DB row / insert dict to API-friendly dict."""
    d = dict(row)
    d["read"] = bool(d.get("read", 0))
    return d
