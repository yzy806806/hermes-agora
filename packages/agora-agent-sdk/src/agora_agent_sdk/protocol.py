"""Protocol models for Agora Agent SDK — no FastAPI dependencies.

Subset of coordinator-side models needed by agents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WS message types used in agent-coordinator communication."""

    # Agent → Coordinator
    REGISTER = "REGISTER"
    SPEAK = "SPEAK"
    VOTE = "VOTE"
    HEARTBEAT = "HEARTBEAT"
    TASK_STATUS = "TASK_STATUS"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_STARTED = "TASK_STARTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    NEW_MOTION = "NEW_MOTION"
    # Coordinator → Agent
    WELCOME = "WELCOME"
    SPEECH_ADDED = "SPEECH_ADDED"
    VOTE_CONFIRMED = "VOTE_CONFIRMED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"
    ERROR = "ERROR"
    DEVILS_ADVOCATE_REQUEST = "DEVILS_ADVOCATE_REQUEST"
    DEVILS_ADVOCATE_RESPONSE = "DEVILS_ADVOCATE_RESPONSE"


class WSMessage(BaseModel):
    """Generic WS message envelope."""

    type: MessageType
    motion_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Per-agent runtime config received in WELCOME message."""

    agent_id: str = ""
    name: str = ""
    agent_type: str = "custom"
    capabilities: list[str] = Field(default_factory=list)
    model: str = ""
    max_concurrent_tasks: int = 2
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 120
    tpm_limit: int = 10000
    tpm_burst_factor: float = 1.5
    allowed_discussion_roles: list[str] = Field(
        default_factory=lambda: ["participant"]
    )
    auto_accept_tasks: bool = False


class RegistrationResult(BaseModel):
    """Result of agent registration."""

    agent_id: str = ""
    token: str = ""
    status: str = "ok"
    message: str = ""
    agent_token: str = ""
class MotionResult(BaseModel):
    """Result of create_motion call."""

    motion_id: str
    status: str = "ok"
    message: str = ""


class SpeechResult(BaseModel):
    """Result of speak call."""

    success: bool = True
    message: str = ""


class VoteResult(BaseModel):
    """Result of vote call."""

    success: bool = True
    confirmed: bool = False
    message: str = ""


class TaskNode(BaseModel):
    """Task assignment payload from coordinator."""

    task_id: str
    title: str = ""
    description: str = ""
    parent_id: Optional[str] = None
