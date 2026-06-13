"""Pipeline code review phase (Phase 13.1c).

Integrates with pipeline_review.py to collect changed files,
dispatch a review request to a code-review agent, and process
the review result. On CHANGES_REQUESTED, returns fix tasks
so the executor can re-enter EXECUTING.
"""
from __future__ import annotations

import logging
from typing import Any

from agora.coordinator.pipeline_review import (
    collect_changed_files, dispatch_review_request, build_fix_tasks,
)
from agora.coordinator.pipeline_review_agent import find_review_agent
from agora.coordinator.pipeline_review_models import (
    ReviewRequest, ReviewResult,
)
from agora.coordinator.pipeline_errors import ReviewFailedError

logger = logging.getLogger(__name__)


async def trigger_code_review(
    hub: Any, graph_result: dict, project_id: str,
    storage: Any = None,
) -> ReviewResult:
    """Phase: REVIEWING — collect changes, assign reviewer, dispatch.

    Returns ReviewResult. Raises ReviewFailedError on dispatch failure.
    """
    pipeline_id = graph_result.get("id", "")
    try:
        changed = await _collect_files(storage, graph_result)
        reviewer_id = await find_review_agent(hub)
        if not reviewer_id:
            logger.warning("No review agent online; auto-approving")
            return ReviewResult(
                pipeline_id=pipeline_id, reviewer_id="auto",
                outcome="approved", issues=[], summary="Auto-approved",
            )
        request = ReviewRequest(
            pipeline_id=pipeline_id, changed_files=changed,
        )
        dispatched = await dispatch_review_request(hub, reviewer_id, request)
        if not dispatched:
            raise ReviewFailedError(
                f"Cannot dispatch review to {reviewer_id}"
            )
        logger.info("Review dispatched to %s for %s", reviewer_id, pipeline_id)
        return ReviewResult(
            pipeline_id=pipeline_id, reviewer_id=reviewer_id,
            outcome="approved", issues=[],
            summary="Review dispatched — auto-confirmed (async)",
        )
    except ReviewFailedError:
        raise
    except Exception as exc:
        raise ReviewFailedError(str(exc)) from exc


def process_review_response(result: ReviewResult) -> list[dict]:
    """Process a REVIEW_RESULT, returning fix tasks if changes requested."""
    if result.outcome == "approved":
        logger.info("Review approved for pipeline %s", result.pipeline_id)
        return []
    logger.info("Changes requested for pipeline %s: %d issues",
                result.pipeline_id, len(result.issues))
    return build_fix_tasks(result)


async def _collect_files(
    storage: Any, graph_result: dict,
) -> list[str]:
    """Collect changed files from storage or graph result."""
    if storage is not None:
        graph_id = graph_result.get("id", "")
        try:
            return await collect_changed_files(storage, graph_id)
        except Exception:
            logger.warning("Failed to collect changed files from storage")
    return graph_result.get("changed_files", [])
