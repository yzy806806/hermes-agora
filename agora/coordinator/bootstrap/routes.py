"""Bootstrap API routes — /api/bootstrap/* endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .approval_flow import ApprovalFlow
from .schedule_checker import check_scheduled_triggers, update_schedule_run
from .trigger_manager import TriggerManager, TriggerType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])

# Module-level singletons — set by BootstrapEngine.init()
_trigger_mgr: Optional[TriggerManager] = None
_approval_flow: Optional[ApprovalFlow] = None
_db_path: Optional[str] = None


def init_bootstrap(
    trigger_mgr: TriggerManager,
    approval_flow: ApprovalFlow,
    db_path: str,
) -> None:
    global _trigger_mgr, _approval_flow, _db_path
    _trigger_mgr = trigger_mgr
    _approval_flow = approval_flow
    _db_path = db_path


# --- Request / Response models ---


class TriggerRequest(BaseModel):
    topic: str
    context: str
    source: str = "user"
    trigger_type: str = "user_requested"
    priority: int = 0


class ApprovalDecideRequest(BaseModel):
    approval_id: str
    approved: bool
    approved_by: str = "user"
    feedback: Optional[str] = None


class ScheduleCreateRequest(BaseModel):
    name: str
    cron_expression: str
    topic_template: str


class ScheduleUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    topic_template: Optional[str] = None


# --- Trigger endpoints ---


@router.post("/trigger")
async def create_trigger(req: TriggerRequest) -> dict:
    if _trigger_mgr is None:
        raise HTTPException(503, "Bootstrap not initialized")
    try:
        tt = TriggerType(req.trigger_type)
    except ValueError:
        raise HTTPException(400, f"Invalid trigger_type: {req.trigger_type}")
    tid = await _trigger_mgr.create_trigger(
        trigger_type=tt, topic=req.topic,
        source=req.source, context=req.context,
        priority=req.priority,
    )
    return {"trigger_id": tid, "status": "created"}


@router.get("/triggers")
async def list_triggers(status: Optional[str] = None) -> dict:
    if _trigger_mgr is None:
        raise HTTPException(503, "Bootstrap not initialized")
    triggers = await _trigger_mgr.get_pending_triggers(limit=50)
    return {"triggers": triggers, "total": len(triggers)}
