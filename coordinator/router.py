"""HTTP REST API routes for the Agora Coordinator service.

Provides endpoints for agent management, motion CRUD, and result queries.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException

from .models import (
    AgentInfo,
    AgentRegisterRequest,
    AssessmentResponse,
    Motion,
    MotionCreateRequest,
    MotionHistoryResponse,
    MotionListResponse,
    MotionResultResponse,
    MotionStatus,
    VotingMethod,
)
from .state import InvalidTransitionError, StateMachine
from .storage import Storage
from .ws import manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level singletons — set by main.py during app startup
_storage: Optional[Storage] = None
_state_machine: Optional[StateMachine] = None


def init_deps(storage: Storage, state_machine: StateMachine) -> None:
    """Initialize module dependencies. Called once at app startup."""
    global _storage, _state_machine
    _storage = storage
    _state_machine = state_machine
    manager.set_deps(storage, state_machine)


def _get_storage() -> Storage:
    if _storage is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _storage


def _get_sm() -> StateMachine:
    if _state_machine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _state_machine


# ---------------------------------------------------------------------------
# Agent API
# ---------------------------------------------------------------------------


@router.post("/agents/register", response_model=AgentInfo)
async def register_agent(request: AgentRegisterRequest) -> AgentInfo:
    """Register a new agent in the system."""
    storage = _get_storage()
    existing = await storage.get_agent(request.agent_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Agent already registered")

    data = await storage.register_agent(
        agent_id=request.agent_id,
        name=request.name,
        model=request.model,
        hermes_endpoint=request.hermes_endpoint,
        capabilities=request.capabilities,
        role=request.role.value,
    )
    return AgentInfo(**data)


@router.delete("/agents/{agent_id}")
async def deregister_agent(agent_id: str) -> dict:
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
# Motion API
# ---------------------------------------------------------------------------


@router.post("/motions", response_model=Motion)
async def create_motion(request: MotionCreateRequest) -> Motion:
    """Create a new motion (topic for discussion)."""
    storage = _get_storage()
    data = await storage.create_motion(
        title=request.title,
        description=request.description,
        rounds=request.rounds,
        voting_method=request.voting_method.value,
        context=request.context or "",
    )
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
async def start_motion(motion_id: str) -> dict:
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
async def force_vote(motion_id: str) -> dict:
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
