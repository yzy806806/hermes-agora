"""Pipeline review message handler (Phase 13.1c).

Handles incoming REVIEW_RESULT messages from review agents
and registers fix tasks in storage when changes are requested.
"""
from __future__ import annotations

import logging
from typing import Any

from agora.coordinator.pipeline_review_models import (
    ReviewIssue, ReviewResult,
)

logger = logging.getLogger(__name__)


def parse_review_result(payload: dict) -> ReviewResult:
    """Parse a REVIEW_RESULT WebSocket payload into ReviewResult.

    Validates required fields and normalizes issue data.
    """
    issues = []
    for raw in payload.get("issues", []):
        issues.append(ReviewIssue(
            file=raw["file"],
            line=raw.get("line"),
            severity=raw["severity"],
            description=raw["description"],
        ))
    return ReviewResult(
        pipeline_id=payload["pipeline_id"],
        reviewer_id=payload["reviewer_id"],
        outcome=payload["outcome"],
        issues=issues,
        summary=payload.get("summary", ""),
    )


async def process_incoming_review_result(
    result: ReviewResult, storage: Any,
) -> list[str]:
    """Process a REVIEW_RESULT from a review agent.

    If approved, returns an empty list.
    If changes_requested, registers fix tasks in storage
    and returns the list of new task IDs.

    Args:
        result: Parsed ReviewResult.
        storage: Storage backend for task creation.

    Returns:
        List of newly created fix task IDs (empty if approved).
    """
    if result.outcome == "approved":
        logger.info("Review approved for pipeline %s", result.pipeline_id)
        return []
    logger.info(
        "Changes requested for pipeline %s: %d issues",
        result.pipeline_id, len(result.issues),
    )
    return await register_fix_tasks(result, storage)


async def register_fix_tasks(
    result: ReviewResult, storage: Any,
) -> list[str]:
    """Create fix tasks in storage for each review issue.

    Returns the list of newly created task IDs.
    """
    task_ids: list[str] = []
    for issue in result.issues:
        task_id = await storage.create_task({
            "type": "fix",
            "file": issue.file,
            "line": issue.line,
            "severity": issue.severity,
            "description": issue.description,
            "reviewer_id": result.reviewer_id,
            "pipeline_id": result.pipeline_id,
            "status": "pending",
        })
        task_ids.append(task_id)
    logger.info("Registered %d fix tasks for pipeline %s",
                len(task_ids), result.pipeline_id)
    return task_ids
