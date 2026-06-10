"""HTTP REST API routes for the Agora Coordinator service.

Provides endpoints for agent management, motion CRUD, and result queries.
Phase 9.3: Updated /agents/register + admin approve/reject/suspend endpoints.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import Response

from .config import settings
from .models import (
    AgentInfo,
    AgentRegisterRequest,
    AgentRegistrationResponse,
    AgentStatus,
    AssessmentResponse,
    Motion,
    MotionCreateRequest,
    MotionHistoryResponse,
    MotionListResponse,
    MotionResultResponse,
    MotionStatus,
    VotingMethod,
)
from .rbac import Permission, Role, get_current_role, requires
from .state import InvalidTransitionError, StateMachine
from .storage import Storage
from .ws import manager
from .curator import DiscussionCurator
from .observability.metrics import collect_metrics
from .observability.trace import get_trace_id, set_trace_id

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level singletons — set by main.py during app startup
_storage: Optional[Storage] = None
_state_machine: Optional[StateMachine] = None
_curator: Optional[DiscussionCurator] = None


def init_deps(storage: Storage, state_machine: StateMachine) -> None:
    """Initialize module dependencies. Called once at app startup."""
    global _storage, _state_machine, _curator
    _storage = storage
    _state_machine = state_machine
    _curator = DiscussionCurator(storage, storage.db_path)
    manager.set_deps(storage, state_machine)


def _get_storage() -> Storage:
    if _storage is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _storage


def _get_sm() -> StateMachine:
    if _state_machine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _state_machine


def _require_admin(authorization: str = Header("")) -> None:
    """Raise 401 if admin token not set or doesn't match."""
    admin_token = settings.admin_token
    if not admin_token:
        raise HTTPException(status_code=501, detail="Admin token not configured")
    token = authorization.removeprefix("Bearer ").strip()
    if token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Observability API
# ---------------------------------------------------------------------------


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """Prometheus-format metrics endpoint."""
    body, content_type = collect_metrics()
    return Response(content=body, media_type=content_type)


# ---------------------------------------------------------------------------
# Agent API
# ---------------------------------------------------------------------------


@router.post("/agents/register", response_model=AgentRegistrationResponse,
             status_code=201)
@requires(Permission.AGENT_REGISTER)
async def register_agent(
    request: AgentRegisterRequest,
    _rbac_role: Role | None = Depends(get_current_role),
) -> AgentRegistrationResponse:
    """Register a new agent. Returns agent_token for WS auth.

    If AGORA_REQUIRE_APPROVAL=true: agent is PENDING until admin approves.
    If AGORA_REQUIRE_APPROVAL=false (default): auto-approved.
    """
    storage = _get_storage()
    existing = await storage.get_agent(request.agent_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Agent already registered")

    agent_token = f"ag-{secrets.token_hex(16)}"
    require_approval = settings.require_approval
    is_approved = not require_approval
    approval_status = "approved" if is_approved else "pending"

    await storage.register_agent(
        agent_id=request.agent_id,
        name=request.name,
        model=request.model,
        capabilities=request.capabilities,
        role="participant",
        agent_type=request.agent_type.value,
        max_concurrent_tasks=request.max_concurrent_tasks,
        agent_token=agent_token,
        is_approved=is_approved,
        approval_status=approval_status,
    )

    message = (
        "Registration successful. You can now connect via WebSocket."
        if is_approved
        else "Registration pending approval. An admin must approve before you can connect."
    )

    return AgentRegistrationResponse(
        agent_id=request.agent_id,
        status=AgentStatus(approval_status),
        agent_token=agent_token,
        message=message,
    )


@router.delete("/agents/{agent_id}")
@requires(Permission.ADMIN_FULL)
async def deregister_agent(
    agent_id: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Deregister an agent from the system."""
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.deregister_agent(agent_id)
    return {"status": "ok"}


@router.get("/agents", response_model=list[AgentInfo])
async def list_agents() -> list[AgentInfo]:
    """List all registered agents."""
    storage = _get_storage()
    agents = await storage.list_agents()
    return [AgentInfo(**a) for a in agents]


# ---------------------------------------------------------------------------
# Admin API (Phase 9.3)
# ---------------------------------------------------------------------------


@router.get("/admin/agents", response_model=list[AgentInfo])
@requires(Permission.ADMIN_FULL)
async def admin_list_agents(
    authorization: str = Header(""),
    _rbac_role: Role | None = Depends(get_current_role),
) -> list[AgentInfo]:
    """List all agents including approval status. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agents = await storage.list_agents()
    return [AgentInfo(**a) for a in agents]


@router.post("/admin/agents/{agent_id}/approve")
@requires(Permission.AGENT_APPROVE)
async def admin_approve_agent(
    agent_id: str,
    authorization: str = Header(""),
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Approve a pending agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, True, "approved")
    return {"agent_id": agent_id, "status": "approved"}


@router.post("/admin/agents/{agent_id}/reject")
@requires(Permission.ADMIN_FULL)
async def admin_reject_agent(
    agent_id: str,
    authorization: str = Header(""),
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Reject a pending agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, False, "rejected")
    return {"agent_id": agent_id, "status": "rejected"}


@router.post("/admin/agents/{agent_id}/suspend")
@requires(Permission.ADMIN_FULL)
async def admin_suspend_agent(
    agent_id: str,
    authorization: str = Header(""),
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Suspend a previously approved agent. Admin only."""
    _require_admin(authorization)
    storage = _get_storage()
    agent = await storage.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    await storage.set_agent_approval(agent_id, False, "suspended")
    return {"agent_id": agent_id, "status": "suspended"}


# ---------------------------------------------------------------------------
# Motion API
# ---------------------------------------------------------------------------


@router.post("/motions", response_model=Motion)
@requires(Permission.DISCUSSION_CREATE)
async def create_motion(
    request: MotionCreateRequest,
    _rbac_role: Role | None = Depends(get_current_role),
) -> Motion:
    """Create a new motion (topic for discussion)."""
    storage = _get_storage()
    data = await storage.create_motion(
        title=request.title,
        description=request.description,
        rounds=request.rounds,
        voting_method=request.voting_method.value,
        context=request.context or "",
    )
    if _curator is not None:
        try:
            optimized = await _curator.optimize_motion(data)
            data.update(optimized)
        except Exception as exc:
            logger.warning("Curator optimization failed: %s", exc)
    return Motion(**data)


@router.get("/motions", response_model=MotionListResponse)
async def list_motions(
    status: Optional[MotionStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> MotionListResponse:
    """List motions, optionally filtered by status."""
    storage = _get_storage()
    motions_data = await storage.list_motions(
        status=status.value if status else None,
        limit=limit,
        offset=offset,
    )
    motions = [Motion(**m) for m in motions_data]
    return MotionListResponse(
        motions=motions, total=len(motions), limit=limit, offset=offset
    )


@router.get("/motions/{motion_id}", response_model=Motion)
async def get_motion(motion_id: str) -> Motion:
    """Get details of a specific motion."""
    storage = _get_storage()
    data = await storage.get_motion(motion_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    return Motion(**data)


@router.post("/motions/{motion_id}/start")
@requires(Permission.DISCUSSION_CREATE)
async def start_motion(
    motion_id: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Start discussion on a draft motion."""
    sm = _get_sm()
    storage = _get_storage()
    try:
        new_status = await sm.transition(motion_id, "start")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    motion = await storage.get_motion(motion_id)
    await manager.broadcast(
        {
            "type": "NEW_MOTION",
            "motion_id": motion_id,
            "payload": motion,
        }
    )
    return {"status": "started", "current_status": new_status.value}


# ---------------------------------------------------------------------------
# History / Result API
# ---------------------------------------------------------------------------


@router.get("/motions/{motion_id}/history", response_model=MotionHistoryResponse)
async def get_history(motion_id: str) -> MotionHistoryResponse:
    """Get discussion history (messages + votes) for a motion."""
    storage = _get_storage()
    motion = await storage.get_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    messages = await storage.get_messages(motion_id)
    votes = await storage.get_votes(motion_id)
    return MotionHistoryResponse(messages=messages, votes=votes)


@router.get("/motions/{motion_id}/result", response_model=MotionResultResponse)
async def get_result(motion_id: str) -> MotionResultResponse:
    """Get the final result of a closed motion."""
    storage = _get_storage()
    motion = await storage.get_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] != MotionStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Motion not closed yet")

    vote_summary = await storage.get_vote_summary(motion_id)
    decision = motion.get("decision", "no_consensus")
    rationale = motion.get("rationale", "")
    action_items = motion.get("action_items", [])

    return MotionResultResponse(
        motion_id=motion_id,
        decision=decision,
        votes=vote_summary.get("counts", {}),
        rationale=rationale,
        action_items=action_items,
    )


# ---------------------------------------------------------------------------
# Phase 2: Smart Discussion & Advanced Voting API
# ---------------------------------------------------------------------------


@router.get("/motions/{motion_id}/assessment",
            response_model=AssessmentResponse)
async def get_assessment(motion_id: str) -> AssessmentResponse:
    """Get the latest assessment for a motion's discussion."""
    storage = _get_storage()
    motion = await storage.get_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")

    assessment = await storage.get_latest_assessment(motion_id)
    if assessment is None:
        raise HTTPException(
            status_code=404, detail="No assessment found")

    return AssessmentResponse(
        motion_id=motion_id,
        result=assessment.get("result", ""),
        consensus_level=assessment.get("consensus_level", ""),
        metrics=assessment.get("metrics", {}),
        rationale=assessment.get("rationale", ""),
        recommendations=assessment.get("recommendations", []),
    )


@router.post("/motions/{motion_id}/force-vote")
@requires(Permission.DISCUSSION_VOTE)
async def force_vote(
    motion_id: str,
    _rbac_role: Role | None = Depends(get_current_role),
) -> dict:
    """Force a motion into voting phase regardless of round progress."""
    sm = _get_sm()
    storage = _get_storage()
    motion = await storage.get_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    if motion["status"] not in ("discussing", "assessing", "devils_advocate"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot force vote from status {motion['status']}")

    try:
        new_status = await sm.transition(motion_id, "start_voting")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await manager.broadcast({
        "type": "REQUEST_VOTE",
        "motion_id": motion_id,
        "payload": {
            "voting_method": motion.get("voting_method",
                                        "simple_majority"),
            "forced": True,
        },
    })
    return {"status": "voting_started", "current_status": new_status.value}
