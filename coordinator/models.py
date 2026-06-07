"""Pydantic data models for the Agora Coordinator service.

Defines all request/response models, enums, and WebSocket message types.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MessageType(str, Enum):
    """WebSocket message types."""

    REGISTER = "REGISTER"
    DEREGISTER = "DEREGISTER"
    NEW_MOTION = "NEW_MOTION"
    REQUEST_SPEAK = "REQUEST_SPEAK"
    SPEAK = "SPEAK"
    BROADCAST = "BROADCAST"
    ROUND_COMPLETE = "ROUND_COMPLETE"
    REQUEST_VOTE = "REQUEST_VOTE"
    VOTE = "VOTE"
    VOTE_CONFIRMED = "VOTE_CONFIRMED"
    RESULT = "RESULT"
    ERROR = "ERROR"
    PING = "PING"
    PONG = "PONG"
    WELCOME = "WELCOME"
    AGENT_OFFLINE = "AGENT_OFFLINE"
    # Phase 2: smart discussion
    ASSESSMENT = "ASSESSMENT"
    TOPIC_REDIRECT = "TOPIC_REDIRECT"
    DEVILS_ADVOCATE_REQUEST = "DEVILS_ADVOCATE_REQUEST"
    DEVILS_ADVOCATE_RESPONSE = "DEVILS_ADVOCATE_RESPONSE"


class MotionStatus(str, Enum):
    """Motion lifecycle states."""

    DRAFT = "draft"
    DISCUSSING = "discussing"
    ASSESSING = "assessing"
    DEVILS_ADVOCATE = "devils_advocate"
    VOTING = "voting"
    CLOSED = "closed"


class VotingMethod(str, Enum):
    """Supported voting methods."""

    SIMPLE_MAJORITY = "simple_majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    # Phase 2: advanced voting
    BORDA_COUNT = "borda_count"
    RANKED_CHOICE = "ranked_choice"
    APPROVAL = "approval"
    RANGE = "range"
    INSTANT_RUNOFF = "instant_runoff"

class Stance(str, Enum):
    """Agent stance on a motion."""

    SUPPORT = "support"
    OPPOSE = "oppose"
    NEUTRAL = "neutral"


class VoteChoice(str, Enum):
    """Vote options."""

    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class AgentRole(str, Enum):
    """Agent roles in discussions."""

    COORDINATOR = "coordinator"
    PARTICIPANT = "participant"
    EXPERT = "expert"
    DEVIL_ADVOCATE = "devil_advocate"
    OBSERVER = "observer"


class DiscussionRole(str, Enum):
    """Discussion roles for multi-model diversity (Phase 6.5)."""

    SUPPORT_ADVOCATE = "support_advocate"
    OPPOSE_ADVOCATE = "oppose_advocate"
    EXPERT = "expert"
    NEUTRAL = "neutral"
    FACT_CHECKER = "fact_checker"
    CREATIVE = "creative"


class Decision(str, Enum):
    """Final decision outcomes."""

    ADOPTED = "adopted"
    REJECTED = "rejected"
    NO_CONSENSUS = "no_consensus"


# ---------------------------------------------------------------------------
# WebSocket Message
# ---------------------------------------------------------------------------


class WSMessage(BaseModel):
    """Generic WebSocket message envelope."""

    type: MessageType
    motion_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent Models
# ---------------------------------------------------------------------------


class AgentRegisterRequest(BaseModel):
    """Request body for agent registration."""

    agent_id: str
    name: str
    hermes_endpoint: str = "http://localhost:8080"
    model: str
    capabilities: list[str] = Field(default_factory=list)
    role: AgentRole = AgentRole.PARTICIPANT


class AgentInfo(BaseModel):
    """Agent information stored in the system."""

    agent_id: str
    name: str
    hermes_endpoint: str = ""
    model: str = ""
    capabilities: list[str] = Field(default_factory=list)
    role: AgentRole = AgentRole.PARTICIPANT
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_online: bool = False
    last_seen: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Motion Models
# ---------------------------------------------------------------------------


class MotionCreateRequest(BaseModel):
    """Request body for creating a motion."""

    title: str
    description: str
    context: Optional[str] = None
    rounds: int = 3
    voting_method: VotingMethod = VotingMethod.SIMPLE_MAJORITY
    # Phase 2: advanced voting options
    voting_options: Optional[list[str]] = None
    voting_config: Optional[dict[str, Any]] = None


class Motion(BaseModel):
    """A discussion motion/topic."""

    id: str
    title: str
    description: str
    context: Optional[str] = None
    rounds: int = 3
    voting_method: VotingMethod = VotingMethod.SIMPLE_MAJORITY
    status: MotionStatus = MotionStatus.DRAFT
    current_round: int = 0
    decision: Optional[Decision] = None
    rationale: Optional[str] = None
    action_items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None

    # Phase 2: smart discussion fields
    smart_mode: bool = True
    assessment_config: Optional[dict[str, Any]] = None
    devils_advocate_count: int = 0
    focus_areas: list[str] = Field(default_factory=list)
    early_vote_triggered: bool = False


# ---------------------------------------------------------------------------
# Speak & Vote Models
# ---------------------------------------------------------------------------


class SpeakRequest(BaseModel):
    """Request body for submitting a speech."""

    motion_id: str
    round: int
    stance: Stance
    content: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class VoteRequest(BaseModel):
    """Request body for casting a vote."""

    motion_id: str
    vote: VoteChoice
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: Optional[str] = None


# Phase 2: advanced vote request models

class MultipleChoiceVoteRequest(BaseModel):
    """Request body for multiple-choice voting."""

    motion_id: str
    type: str = "multiple_choice"
    vote: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: Optional[str] = None


class RankingVoteRequest(BaseModel):
    """Request body for ranked-choice voting."""

    motion_id: str
    type: str = "ranking"
    ranking: list[str]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ApprovalVoteRequest(BaseModel):
    """Request body for approval voting."""

    motion_id: str
    type: str = "approval"
    approved: list[str]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class RangeVoteRequest(BaseModel):
    """Request body for range/score voting."""

    motion_id: str
    type: str = "range"
    scores: dict[str, float]
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class MotionListResponse(BaseModel):
    """Paginated motion list response."""

    motions: list[Motion]
    total: int
    limit: int
    offset: int


class MotionHistoryResponse(BaseModel):
    """Discussion history for a motion."""

    messages: list[dict[str, Any]]
    votes: list[dict[str, Any]]


class MotionResultResponse(BaseModel):
    """Final result of a motion discussion."""

    motion_id: str
    decision: Decision
    votes: dict[str, int]
    rationale: str
    action_items: list[str]


class ErrorResponse(BaseModel):
    """Standard error response."""

    type: str = "ERROR"
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class AssessmentResponse(BaseModel):
    """Response body for motion assessment."""

    motion_id: str
    result: str
    consensus_level: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    recommendations: list[str] = Field(default_factory=list)
