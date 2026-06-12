"""Session-related models for the Agora Agent SDK.

These models mirror the coordinator-side session API and are
used by SessionStore to record/query agent sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    """A single session for an agent. Stored in Agora DB."""

    id: str = Field(default_factory=lambda: _generate_ulid())
    agent_id: str
    project_id: str = ""
    session_type: str = "task_execution"
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ended_at: Optional[datetime] = None
    input_messages: list[dict[str, Any]] = Field(default_factory=list)
    output_messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    outcome: str = "success"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionFilter(BaseModel):
    """Query parameters for searching sessions."""

    agent_id: Optional[str] = None
    project_id: Optional[str] = None
    session_type: Optional[str] = None
    outcome: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SessionNote(BaseModel):
    """A note attached to a session by an agent."""

    content: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def _generate_ulid() -> str:
    """Generate a simple ULID-like ID (timestamp + random)."""
    import random
    import time

    ts = int(time.time() * 1000)
    rand_part = random.randint(0, 0xFFFFFF)
    return f"{ts:013d}{rand_part:06d}"
