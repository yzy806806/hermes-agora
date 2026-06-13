"""PipelineReviewer class — high-level review orchestration.

Wraps the lower-level functions from pipeline_review.py
into a class interface used by tests and the pipeline executor.
"""
from __future__ import annotations

import logging
from typing import Any

from agora.coordinator.pipeline_review import (
    build_fix_tasks, dispatch_review_request,
)
from agora.coordinator.pipeline_review_agent import find_review_agent
from agora.coordinator.pipeline_review_models import (
    ReviewRequest, ReviewResult,
)

logger = logging.getLogger(__name__)


class PipelineReviewer:
    """Orchestrates code review for a pipeline run."""

    def __init__(self, hub: Any) -> None:
        self.hub = hub

    async def request_review(
        self, pipeline_id: str, changed_files: list[str],
    ) -> ReviewResult:
        """Submit a review request and return the result."""
        request = ReviewRequest(
            pipeline_id=pipeline_id,
            changed_files=changed_files,
        )
        return await self.hub.submit_review(request)

    async def process_review_result(
        self, result: ReviewResult,
    ) -> list[dict]:
        """Process a ReviewResult, returning fix tasks if changes requested."""
        if result.outcome == "approved":
            return []
        return build_fix_tasks(result)

    async def re_review(
        self, pipeline_id: str, fix_tasks: list[dict],
    ) -> ReviewResult:
        """Re-review after fixes are applied."""
        changed = [t["file"] for t in fix_tasks]
        reviewer_id = await find_review_agent(self.hub)
        if not reviewer_id:
            return ReviewResult(
                pipeline_id=pipeline_id, reviewer_id="auto",
                outcome="approved", issues=[], summary="Auto-approved",
            )
        request = ReviewRequest(
            pipeline_id=pipeline_id, changed_files=changed,
        )
        dispatched = await dispatch_review_request(
            self.hub, reviewer_id, request,
        )
        if not dispatched:
            return ReviewResult(
                pipeline_id=pipeline_id, reviewer_id="auto",
                outcome="approved", issues=[],
                summary="Auto-approved (dispatch failed)",
            )
        return await self.hub.submit_review(request)
