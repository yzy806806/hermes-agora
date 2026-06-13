"""Tests for pipeline_phase_release.py (Phase 13.1d).

Tests: trigger_release, _build_request, _dispatch_release,
process_release_result.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.pipeline_phase_release import (
    trigger_release, process_release_result, _build_request,
)
from agora.coordinator.pipeline_release_models import ReleaseResult
from agora.coordinator.pipeline_errors import ReleaseFailedError


@pytest.mark.asyncio
async def test_trigger_release_no_agent():
    """Raises ReleaseFailedError when no release agent online."""
    hub = MagicMock()
    hub.get_online_agents.return_value = []
    hub._app_state = None
    with pytest.raises(ReleaseFailedError, match="No release agent"):
        await trigger_release(hub, {"id": "g1"}, "proj-1")


@pytest.mark.asyncio
async def test_trigger_release_success():
    """Sends TASK_ASSIGNED and returns release id."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["releaser-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=True)
    result = await trigger_release(hub, {"id": "g1"}, "proj-1")
    assert result == "release-g1"
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["type"] == "TASK_ASSIGNED"
    assert msg["payload"]["task_type"] == "RELEASE"


@pytest.mark.asyncio
async def test_trigger_release_send_fails():
    """Raises ReleaseFailedError when hub.send returns False."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["releaser-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=False)
    with pytest.raises(ReleaseFailedError, match="Cannot reach"):
        await trigger_release(hub, {"id": "g1"}, "proj-1")


@pytest.mark.asyncio
async def test_trigger_release_with_review_summary():
    """Passes review_summary through to the release request."""
    hub = MagicMock()
    hub.get_online_agents.return_value = ["releaser-1"]
    hub._app_state = None
    hub.send = AsyncMock(return_value=True)
    await trigger_release(hub, {"id": "g1"}, "proj-1", "LGTM")
    msg = hub.send.call_args[0][1]
    req = msg["payload"]["request"]
    assert req["review_summary"] == "LGTM"


def test_build_request():
    """_build_request populates ReleaseRequest from graph result."""
    graph = {"id": "g2", "changed_files": ["a.py", "b.py"]}
    req = _build_request(graph, "proj-2", "Approved")
    assert req.pipeline_id == "g2"
    assert req.project_id == "proj-2"
    assert req.changed_files == ["a.py", "b.py"]
    assert req.review_summary == "Approved"


def test_process_release_result_success():
    """Returns version string on success outcome."""
    result = ReleaseResult(
        pipeline_id="p1", releaser_id="r1",
        outcome="success", version="v1.2.0", tag="v1.2.0",
    )
    assert process_release_result(result) == "v1.2.0"


def test_process_release_result_failed():
    """Raises ReleaseFailedError on failed outcome."""
    result = ReleaseResult(
        pipeline_id="p1", releaser_id="r1",
        outcome="failed", error="git push rejected",
    )
    with pytest.raises(ReleaseFailedError, match="git push rejected"):
        process_release_result(result)
