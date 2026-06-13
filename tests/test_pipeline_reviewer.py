"""Unit tests for PipelineReviewer (review phase logic)."""
import pytest
from unittest.mock import AsyncMock, patch

from agora.coordinator.pipeline_reviewer import PipelineReviewer
from agora.coordinator.pipeline_review_models import (
    ReviewIssue, ReviewResult,
)


def _make_reviewer():
    hub = AsyncMock()
    return PipelineReviewer(hub)


@pytest.mark.asyncio
async def test_request_review():
    """request_review submits ReviewRequest and returns result."""
    reviewer = _make_reviewer()
    expected = ReviewResult(
        pipeline_id="p1", reviewer_id="r1",
        outcome="approved", summary="LGTM",
    )
    reviewer.hub.submit_review = AsyncMock(return_value=expected)
    result = await reviewer.request_review("p1", ["a.py", "b.py"])
    assert result.outcome == "approved"
    req = reviewer.hub.submit_review.call_args[0][0]
    assert req.pipeline_id == "p1"
    assert req.changed_files == ["a.py", "b.py"]


@pytest.mark.asyncio
async def test_process_review_approved():
    """Approved review returns no fix tasks."""
    reviewer = _make_reviewer()
    result = ReviewResult(
        pipeline_id="p1", reviewer_id="r1",
        outcome="approved", summary="ok",
    )
    tasks = await reviewer.process_review_result(result)
    assert tasks == []


@pytest.mark.asyncio
async def test_process_review_changes_requested():
    """Changes requested returns fix tasks for each issue."""
    reviewer = _make_reviewer()
    result = ReviewResult(
        pipeline_id="p1", reviewer_id="r1",
        outcome="changes_requested",
        issues=[
            ReviewIssue(file="a.py", line=5, severity="critical",
                        description="bug"),
            ReviewIssue(file="b.py", severity="minor",
                        description="style"),
        ],
    )
    tasks = await reviewer.process_review_result(result)
    assert len(tasks) == 2
    assert tasks[0]["type"] == "fix"
    assert tasks[0]["file"] == "a.py"
    assert tasks[1]["file"] == "b.py"


@pytest.mark.asyncio
async def test_re_review_no_agent():
    """Re-review auto-approves when no review agent found."""
    reviewer = _make_reviewer()
    with patch(
        "agora.coordinator.pipeline_reviewer.find_review_agent",
        return_value=None,
    ):
        result = await reviewer.re_review("p1", [
            {"file": "a.py"}, {"file": "b.py"},
        ])
    assert result.outcome == "approved"
    assert result.reviewer_id == "auto"
