"""Project artifact CRUD for Agora Coordinator (Phase 12.5a)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from ..models.sessions import Artifact

logger = logging.getLogger(__name__)


async def put_artifact(
    db: aiosqlite.Connection,
    project_id: str, key: str,
    value: bytes, content_type: str,
    created_by: str,
) -> dict:
    """Upsert an artifact. Returns dict representation."""
    now = datetime.now(timezone.utc).isoformat()
    # Check if exists -> update, else insert
    async with db.execute(
        "SELECT id FROM project_artifacts WHERE project_id=? AND key=?",
        [project_id, key],
    ) as cur:
        existing = await cur.fetchone()
    if existing:
        await db.execute(
            """UPDATE project_artifacts
               SET value=?, content_type=?, updated_at=?
               WHERE project_id=? AND key=?""",
            [value, content_type, now, project_id, key],
        )
        aid = dict(existing)["id"]
    else:
        aid = f"{project_id}:{key}"
        await db.execute(
            """INSERT INTO project_artifacts
               (id, project_id, key, value, content_type,
                created_by, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            [aid, project_id, key, value, content_type,
             created_by, now, now],
        )
    await db.commit()
    return {"id": aid, "project_id": project_id, "key": key,
            "content_type": content_type, "created_by": created_by,
            "created_at": now, "updated_at": now}


async def get_artifact(
    db: aiosqlite.Connection,
    project_id: str, key: str,
) -> Optional[dict]:
    async with db.execute(
        "SELECT * FROM project_artifacts WHERE project_id=? AND key=?",
        [project_id, key],
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def delete_artifact(
    db: aiosqlite.Connection,
    project_id: str, key: str,
) -> bool:
    cursor = await db.execute(
        "DELETE FROM project_artifacts WHERE project_id=? AND key=?",
        [project_id, key],
    )
    await db.commit()
    return cursor.rowcount > 0


async def list_artifacts(
    db: aiosqlite.Connection,
    project_id: str,
) -> list[dict]:
    async with db.execute(
        "SELECT * FROM project_artifacts WHERE project_id=?",
        [project_id],
    ) as cur:
        return [dict(r) async for r in cur]
