"""Tests for pipeline_phase_review.py: trigger_code_review,
process_review_response, _collect_files, _extract_from_graph."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.pipeline_phase_review import (
    trigger_code_review, process_review_response,
)
from agora.coordinator.pipeline_review_models import (
    ReviewIssue, ReviewResult,
)
from agora.coordinator.pipeline_errors import ReviewFailedError


@pytest.mark.asyncio
async def test_trigger_review_auto_approve():
    """Auto-approves when no review agent is online."""
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    hub._app_state = None
    result = await trigger_code_review(hub, {"id": "g1"}, "proj-1")
    assert result.outcome == "approved"
    assert result.reviewer_id == "auto"


@pytest.mark.asyncio
async def test_trigger_review_dispatch():
    """Dispatches review to found reviewer."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["reviewer-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=True)
    result = await trigger_code_review(hub, {"id": "g1"}, "proj-1")
    assert result.outcome == "approved"
    assert result.reviewer_id == "reviewer-1"


@pytest.mark.asyncio
async def test_trigger_review_dispatch_fails():
    """Raises ReviewFailedError when dispatch fails."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["reviewer-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=False)
    with pytest.raises(ReviewFailedError):
        await trigger_code_review(hub, {"id": "g1"}, "proj-1")


def test_process_review_approved():
    """Approved review returns no fix tasks."""
    result = ReviewResult(
        pipeline_id="p1", reviewer_id="r1",
        outcome="approved", summary="LGTM",
    )
    assert process_review_response(result) == []


def test_process_review_changes_requested():
    """Changes requested returns fix tasks."""
    result = ReviewResult(
        pipeline_id="p1", reviewer_id="r1",
        outcome="changes_requested",
        issues=[
            ReviewIssue(file="a.py", severity="critical",
                        description="bug"),
        ],
    )
    tasks = process_review_response(result)
    assert len(tasks) == 1
    assert tasks[0]["type"] == "fix"
    assert tasks[0]["file"] == "a.py"


@pytest.mark.asyncio
async def test_trigger_review_with_storage():
    """Collects changed files from storage when provided."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["reviewer-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=True)
    storage = AsyncMock()
    storage.list_tasks = AsyncMock(return_value=[
        {"artifact_paths": ["src/main.py"]},
    ])
    result = await trigger_code_review(
        hub, {"id": "g1"}, "proj-1", storage=storage,
    )
    assert result.outcome == "approved"
    # Verify storage was queried for files
    storage.list_tasks.assert_called_once()
