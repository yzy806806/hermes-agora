"""PipelineRun CRUD for Phase 13 full-auto dev loop."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def create_pipeline_run(
    db: aiosqlite.Connection,
    project_id: str,
    idea: str,
    phase: str = "discussing",
    motion_id: str | None = None,
    graph_id: str | None = None,
) -> dict:
    """Insert a new pipeline run. Returns the full record dict."""
    run_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": run_id, "project_id": project_id, "idea": idea,
        "motion_id": motion_id, "graph_id": graph_id,
        "phase": phase, "started_at": now,
        "completed_at": None, "tasks_total": 0,
        "tasks_completed": 0, "tasks_failed": 0,
        "review_outcome": None, "release_version": None,
        "error": None, "failed_phase": None,
    }
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    await db.execute(
        f"INSERT INTO pipeline_runs ({cols}) VALUES ({placeholders})",
        list(row.values()),
    )
    await db.commit()
    return dict(row)


async def get_pipeline_run(
    db: aiosqlite.Connection, run_id: str,
) -> Optional[dict]:
    """Get a pipeline run by ID, or None."""
    async with db.execute(
        "SELECT * FROM pipeline_runs WHERE id = ?", [run_id],
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def list_pipeline_runs(
    db: aiosqlite.Connection,
    project_id: str | None = None,
    phase: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List pipeline runs with optional filters."""
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if phase is not None:
        clauses.append("phase = ?")
        params.append(phase)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])
    async with db.execute(
        f"SELECT * FROM pipeline_runs {where} "
        f"ORDER BY started_at DESC LIMIT ? OFFSET ?",
        params,
    ) as cur:
        rows = [dict(r) async for r in cur]
    return rows


async def update_pipeline_run(
    db: aiosqlite.Connection,
    run_id: str,
    updates: dict,
) -> Optional[dict]:
    """Update fields on a pipeline run. Returns updated record."""
    allowed = {
        "phase", "motion_id", "graph_id", "completed_at",
        "tasks_total", "tasks_completed", "tasks_failed",
        "review_outcome", "release_version", "error",
        "failed_phase",
    }
    sets, params = [], []
    for k, v in updates.items():
        if k not in allowed:
            continue
        sets.append(f"{k} = ?")
        params.append(v)
    if not sets:
        return await get_pipeline_run(db, run_id)
    params.append(run_id)
    await db.execute(
        f"UPDATE pipeline_runs SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    await db.commit()
    return await get_pipeline_run(db, run_id)


async def delete_pipeline_run(
    db: aiosqlite.Connection, run_id: str,
) -> bool:
    """Delete a pipeline run. Returns True if deleted."""
    cursor = await db.execute(
        "DELETE FROM pipeline_runs WHERE id = ?", [run_id],
    )
    await db.commit()
    return cursor.rowcount > 0


async def count_pipeline_runs(
    db: aiosqlite.Connection,
    project_id: str | None = None,
    phase: str | None = None,
) -> int:
    """Count total pipeline runs matching filters (for pagination)."""
    clauses, params = [], []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(project_id)
    if phase is not None:
        clauses.append("phase = ?")
        params.append(phase)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    async with db.execute(
        f"SELECT COUNT(*) FROM pipeline_runs {where}", params,
    ) as cur:
        row = await cur.fetchone()
    return row[0] if row else 0
