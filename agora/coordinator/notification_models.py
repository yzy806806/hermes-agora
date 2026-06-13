"""Notification models for the Agora Dashboard Enhancement (Phase 13)."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of dashboard notifications."""
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    REVIEW_REQUESTED = "review_requested"
    AGENT_OFFLINE = "agent_offline"
    RATE_LIMITED = "rate_limited"
    DISCUSSION_DEADLOCK = "discussion_deadlock"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Notification(BaseModel):
    """A single notification for dashboard users."""
    id: str
    type: NotificationType
    title: str
    body: str
    project_id: str
    priority: NotificationPriority = NotificationPriority.MEDIUM
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    read: bool = False
