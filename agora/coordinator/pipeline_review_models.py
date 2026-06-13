"""Pipeline review and retry models (Phase 13)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from agora.coordinator.pipeline_models import PipelinePhase


class ReviewIssue(BaseModel):
    """A single issue found during code review."""
    file: str
    line: Optional[int] = None
    severity: Literal["critical", "major", "minor"]
    description: str


class ReviewRequest(BaseModel):
    """Request to review code changes from a pipeline run."""
    pipeline_id: str
    changed_files: list[str] = Field(default_factory=list)
    task_results: list[dict] = Field(default_factory=list)
    test_results: dict = Field(default_factory=dict)


class ReviewResult(BaseModel):
    """Outcome of a code review for a pipeline run."""
    pipeline_id: str
    reviewer_id: str
    outcome: Literal["approved", "changes_requested"]
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str = ""


class PipelineRetryPolicy(BaseModel):
    """Configurable retry policy for pipeline phases."""
    max_retries: int = 3
    retry_delay: int = 30  # seconds
    retryable_phases: set[str] = {"executing", "reviewing", "releasing"}
    max_task_retries: int = 2
