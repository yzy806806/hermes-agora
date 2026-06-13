"""Pipeline code review integration (Phase 13.1c).

Collects changed files from completed tasks, assigns a review
agent via capability matching, dispatches REVIEW_REQUEST over
WebSocket, and processes REVIEW_RESULT responses.
"""
from __future__ import annotations

import logging
from typing import Any

from agora.coordinator.pipeline_review_models import (
    ReviewRequest, ReviewResult,
)
from agora.coordinator.pipeline_review_handler import (
    parse_review_result, process_incoming_review_result,
    register_fix_tasks,
)

logger = logging.getLogger(__name__)


def __getattr__(name: str):
    """Lazy re-export for backward-compatible PipelineReviewer import."""
    if name == "PipelineReviewer":
        from agora.coordinator.pipeline_reviewer import PipelineReviewer
        return PipelineReviewer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def collect_changed_files(
    storage: Any, graph_id: str,
) -> list[str]:
    """Collect artifact_paths from all completed tasks in a graph."""
    tasks = await storage.list_tasks(
        graph_id=graph_id, status="done",
    )
    files: list[str] = []
    for t in tasks:
        for p in t.get("artifact_paths", []):
            if p and p not in files:
                files.append(p)
    return files


async def dispatch_review_request(
    hub: Any, reviewer_id: str, request: ReviewRequest,
) -> bool:
    """Send REVIEW_REQUEST to the reviewer agent via WebSocket."""
    sent = await hub.send(reviewer_id, {
        "type": "REVIEW_REQUEST",
        "payload": request.model_dump(),
    })
    if sent:
        logger.info("Review dispatched to %s for pipeline %s",
                     reviewer_id, request.pipeline_id)
    else:
        logger.warning("Failed to dispatch review to %s", reviewer_id)
    return sent


def build_fix_tasks(result: ReviewResult) -> list[dict]:
    """Create fix task dicts from a changes_requested result."""
    return [
        {
            "type": "fix",
            "file": issue.file,
            "line": issue.line,
            "severity": issue.severity,
            "description": issue.description,
            "reviewer_id": result.reviewer_id,
        }
        for issue in result.issues
    ]
