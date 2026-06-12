"""Pydantic models for session persistence and project artifacts.

Phase 12.5a: Agent self-evolution support.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    """A single session for an agent. Stored in Agora DB."""

    id: str
    agent_id: str
    project_id: str
    session_type: str = "task_execution"
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ended_at: Optional[datetime] = None
    input_messages: list[dict] = Field(default_factory=list)
    output_messages: list[dict] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
    outcome: str = "success"
    metadata: dict = Field(default_factory=dict)


class SessionNote(BaseModel):
    """A note added to a session by an agent."""

    session_id: str
    agent_id: str
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Artifact(BaseModel):
    """A project artifact in the key-value store."""

    id: str
    project_id: str
    key: str
    value: bytes = b""
    content_type: str = "application/octet-stream"
    created_by: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
