"""Approval Flow — user approval for bootstrap discussion results."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalFlow:
    """Manage user approval for discussion results.

    Flow: AI team discusses → generates plan → user approves/rejects
    → approved: tasks generated / rejected: discussion restarts.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def submit_for_approval(
        self, motion_id: str, decision: str,
        rationale: str = "",
        action_items: Optional[list[dict]] = None,
    ) -> str:
        """Create an approval request for a motion result. Returns approval id."""
        now = datetime.utcnow().isoformat()
        items_json = json.dumps(action_items or [], ensure_ascii=False)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO bootstrap_approvals
                   (motion_id, decision, rationale, action_items,
                    approval_status, requested_at)
                   VALUES (?, ?, ?, ?, 'pending', ?)""",
                (motion_id, decision, rationale, items_json, now),
            )
            await db.commit()
            return str(cursor.lastrowid)

    async def get_approval(self, approval_id: str) -> Optional[dict]:
        """Retrieve an approval record by id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bootstrap_approvals WHERE id = ?",
                (approval_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_approval_by_motion(
        self, motion_id: str,
    ) -> Optional[dict]:
        """Retrieve the latest approval record for a motion."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM bootstrap_approvals
                   WHERE motion_id = ?
                   ORDER BY requested_at DESC LIMIT 1""",
                (motion_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_pending(self, limit: int = 20) -> list[dict]:
        """List all pending approvals."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM bootstrap_approvals
                   WHERE approval_status = 'pending'
                   ORDER BY requested_at ASC LIMIT ?""",
                (limit,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def list_all(
        self, status: Optional[str] = None, limit: int = 50,
    ) -> list[dict]:
        """List approvals, optionally filtered by status."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute(
                    """SELECT * FROM bootstrap_approvals
                       WHERE approval_status = ?
                       ORDER BY requested_at DESC LIMIT ?""",
                    (status, limit),
                ) as cur:
                    rows = await cur.fetchall()
            else:
                async with db.execute(
                    """SELECT * FROM bootstrap_approvals
                       ORDER BY requested_at DESC LIMIT ?""",
                    (limit,),
                ) as cur:
                    rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def handle_approval(
        self, approval_id: str, approved: bool,
        approved_by: str = "user",
        feedback: Optional[str] = None,
    ) -> dict:
        """Process an approval decision."""
        now = datetime.utcnow().isoformat()
        status = (
            ApprovalStatus.APPROVED.value
            if approved
            else ApprovalStatus.REJECTED.value
        )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE bootstrap_approvals
                   SET approval_status = ?, approved_by = ?,
                       feedback = ?, processed_at = ?
                   WHERE id = ?""",
                (status, approved_by, feedback, now, approval_id),
            )
            await db.commit()
        if approved:
            return {"status": "approved", "approval_id": approval_id}
        return {
            "status": "rejected",
            "approval_id": approval_id,
            "feedback": feedback,
        }
