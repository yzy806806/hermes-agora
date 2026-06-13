"""Tests for trigger_release and process_release_result (Phase 13.1d)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agora.coordinator.pipeline_phase_release import (
    trigger_release, process_release_result,
)
from agora.coordinator.pipeline_release_models import ReleaseResult
from agora.coordinator.pipeline_errors import ReleaseFailedError


def _hub(releaser_id: str = "releaser-1") -> MagicMock:
    hub = MagicMock()
    hub.get_online_agents.return_value = [releaser_id]
    hub.send = AsyncMock(return_value=True)
    hub._app_state = MagicMock()
    hub._app_state.agent_registry = {
        releaser_id: {"capabilities": ["release"]},
    }
    return hub


class TestTriggerRelease:
    @pytest.mark.asyncio
    async def test_success(self):
        hub = _hub()
        version = await trigger_release(
            hub, {"id": "g1", "changed_files": ["a.py"]},
            "proj-1", "LGTM",
        )
        assert "g1" in version
        hub.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_releaser(self):
        hub = MagicMock()
        hub.get_online_agents.return_value = []
        hub._app_state = MagicMock()
        hub._app_state.agent_registry = {}
        with pytest.raises(ReleaseFailedError, match="No release agent"):
            await trigger_release(hub, {"id": "g1"}, "proj-1")

    @pytest.mark.asyncio
    async def test_send_fails(self):
        hub = _hub()
        hub.send = AsyncMock(return_value=False)
        with pytest.raises(ReleaseFailedError, match="Cannot reach"):
            await trigger_release(hub, {"id": "g1"}, "proj-1")


class TestProcessReleaseResult:
    def test_success_returns_version(self):
        result = ReleaseResult(
            pipeline_id="p1", outcome="success",
            version="0.13.0", tag="v0.13.0",
        )
        assert process_release_result(result) == "0.13.0"

    def test_failure_raises(self):
        result = ReleaseResult(
            pipeline_id="p1", outcome="failed",
            error="push rejected",
        )
        with pytest.raises(ReleaseFailedError, match="push rejected"):
            process_release_result(result)
