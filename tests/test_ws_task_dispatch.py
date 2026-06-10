"""Tests for TASK_STATUS and TASK_ACCEPT_RESULT dispatch in ws_endpoint."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.models import MessageType
from agora.coordinator.ws_endpoint import _route_message


def _make_hub() -> MagicMock:
    """Create a mock hub with storage and state_machine."""
    hub = MagicMock()
    hub._storage = MagicMock()
    hub._state_machine = MagicMock()
    hub.send = AsyncMock()
    return hub


class TestTaskStatusDispatch:
    """TASK_STATUS messages route to handle_task_status."""

    @pytest.mark.asyncio
    async def test_dispatches_to_handle_task_status(self):
        hub = _make_hub()
        msg = json.dumps({
            "type": MessageType.TASK_STATUS,
            "payload": {"task_id": "t-1", "status": "running"},
        })
        handler = AsyncMock()
        with patch(
            "agora.coordinator.ws_endpoint.handle_task_status", handler,
            create=True,
        ):
            # task_exec may not exist yet, so patch at import target
            with patch.dict(
                "sys.modules",
                {"agora.coordinator.task_exec": MagicMock(
                    handle_task_status=handler,
                )},
            ):
                await _route_message("agent1", msg, hub)
        handler.assert_awaited_once()
        call_args = handler.call_args
        assert call_args[0][0] == "agent1"
        assert call_args[0][1] == {"task_id": "t-1", "status": "running"}


class TestTaskAcceptResultDispatch:
    """TASK_ACCEPT_RESULT messages route to handle_task_accept_result."""

    @pytest.mark.asyncio
    async def test_dispatches_to_handle_task_accept_result(self):
        hub = _make_hub()
        msg = json.dumps({
            "type": MessageType.TASK_ACCEPT_RESULT,
            "payload": {"task_id": "t-1", "accepted": True},
        })
        handler = AsyncMock()
        with patch.dict(
            "sys.modules",
            {"agora.coordinator.task_verify": MagicMock(
                handle_task_accept_result=handler,
            )},
        ):
            await _route_message("agent1", msg, hub)
        handler.assert_awaited_once()
        call_args = handler.call_args
        assert call_args[0][0] == "agent1"
        assert call_args[0][1] == {"task_id": "t-1", "accepted": True}


class TestTaskDispatchNoDeps:
    """Task messages are dropped if hub deps are missing."""

    @pytest.mark.asyncio
    async def test_no_storage_returns_early(self):
        hub = MagicMock()
        hub._storage = None
        hub._state_machine = MagicMock()
        msg = json.dumps({
            "type": MessageType.TASK_STATUS,
            "payload": {"task_id": "t-1", "status": "running"},
        })
        # Should not raise, just return early
        await _route_message("agent1", msg, hub)
