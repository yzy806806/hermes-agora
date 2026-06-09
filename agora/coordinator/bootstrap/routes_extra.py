"""Bootstrap API routes — approval and schedule endpoints."""

from __future__ import annotations

import aiosqlite
from typing import Optional

from fastapi import APIRouter, HTTPException

from .routes import (
    _approval_flow,
    _db_path,
    ApprovalDecideRequest,
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
)

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


# --- Approval endpoints ---


@router.post("/approval")
async def submit_approval(
    motion_id: str, decision: str, rationale: str = "",
) -> dict:
    if _approval_flow is None:
        raise HTTPException(503, "Bootstrap not initialized")
    aid = await _approval_flow.submit_for_approval(
        motion_id=motion_id, decision=decision, rationale=rationale,
    )
    return {"approval_id": aid, "status": "pending"}


@router.post("/approval/decide")
async def decide_approval(req: ApprovalDecideRequest) -> dict:
    if _approval_flow is None:
        raise HTTPException(503, "Bootstrap not initialized")
    return await _approval_flow.handle_approval(
        approval_id=req.approval_id, approved=req.approved,
        approved_by=req.approved_by, feedback=req.feedback,
    )


@router.get("/approvals")
async def list_approvals(
    status: Optional[str] = None, limit: int = 50,
) -> dict:
    if _approval_flow is None:
        raise HTTPException(503, "Bootstrap not initialized")
    items = await _approval_flow.list_all(status=status, limit=limit)
    return {"approvals": items, "total": len(items)}


# --- Schedule endpoints ---


@router.get("/schedules")
async def list_schedules() -> dict:
    if _db_path is None:
        raise HTTPException(503, "Bootstrap not initialized")
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bootstrap_schedules",
        ) as cur:
            rows = await cur.fetchall()
            return {"schedules": [dict(r) for r in rows]}


@router.post("/schedules")
async def create_schedule(req: ScheduleCreateRequest) -> dict:
    if _db_path is None:
        raise HTTPException(503, "Bootstrap not initialized")
    async with aiosqlite.connect(_db_path) as db:
        cursor = await db.execute(
            """INSERT INTO bootstrap_schedules
               (name, cron_expression, topic_template)
               VALUES (?, ?, ?)""",
            (req.name, req.cron_expression, req.topic_template),
        )
        await db.commit()
        return {"schedule_id": str(cursor.lastrowid), "status": "created"}


@router.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int, req: ScheduleUpdateRequest,
) -> dict:
    if _db_path is None:
        raise HTTPException(503, "Bootstrap not initialized")
    async with aiosqlite.connect(_db_path) as db:
        parts, vals = [], []
        if req.cron_expression is not None:
            parts.append("cron_expression = ?")
            vals.append(req.cron_expression)
        if req.topic_template is not None:
            parts.append("topic_template = ?")
            vals.append(req.topic_template)
        if req.enabled is not None:
            parts.append("enabled = ?")
            vals.append(int(req.enabled))
        if not parts:
            raise HTTPException(400, "No fields to update")
        vals.append(schedule_id)
        await db.execute(
            f"UPDATE bootstrap_schedules SET {', '.join(parts)} WHERE id = ?",
            vals,
        )
        await db.commit()
    return {"status": "updated"}
