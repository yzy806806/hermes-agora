"""Tests for timeout_checker.py and handle_heartbeat (Phase 9.3c)."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agora.coordinator.timeout_checker import heartbeat_timeout_checker
from agora.coordinator.ws_handlers import handle_heartbeat


class TestHandleHeartbeat:
    @pytest.mark.asyncio
    async def test_updates_load_and_active_tasks(self):
        storage = AsyncMock()
        mgr = AsyncMock()
        payload = {"load": 0.5, "active_tasks": ["t1"]}
        await handle_heartbeat("a1", payload, storage, mgr)
        storage.update_agent_heartbeat.assert_called_once_with(
            "a1", load=0.5, active_tasks=["t1"],
        )

    @pytest.mark.asyncio
    async def test_updates_capabilities_when_provided(self):
        storage = AsyncMock()
        mgr = AsyncMock()
        payload = {"load": 0.0, "capabilities": ["code"]}
        await handle_heartbeat("a1", payload, storage, mgr)
        storage.update_agent_capabilities.assert_called_once_with(
            "a1", ["code"],
        )

    @pytest.mark.asyncio
    async def test_skips_capabilities_when_missing(self):
        storage = AsyncMock()
        mgr = AsyncMock()
        payload = {"load": 0.0}
        await handle_heartbeat("a1", payload, storage, mgr)
        storage.update_agent_capabilities.assert_not_called()

    @pytest.mark.asyncio
    async def test_updates_model_when_provided(self):
        storage = AsyncMock()
        mgr = AsyncMock()
        payload = {"load": 0.0, "model": "gpt-4"}
        await handle_heartbeat("a1", payload, storage, mgr)
        storage.update_agent_model.assert_called_once_with("a1", "gpt-4")

    @pytest.mark.asyncio
    async def test_skips_model_when_missing(self):
        storage = AsyncMock()
        mgr = AsyncMock()
        payload = {"load": 0.0}
        await handle_heartbeat("a1", payload, storage, mgr)
        storage.update_agent_model.assert_not_called()


class TestHeartbeatTimeoutChecker:
    @pytest.mark.asyncio
    async def test_marks_stale_agent_offline(self):
        storage = AsyncMock()
        storage.list_stale_agents = AsyncMock(
            return_value=[{"agent_id": "stale1", "last_seen_at": "old"}]
        )
        storage.set_agent_online = AsyncMock()
        mock_hub = MagicMock()
        mock_hub.broadcast = AsyncMock()
        with patch(
            "agora.coordinator.timeout_checker.manager"
        ) as mock_mgr:
            mock_mgr.get_hub.return_value = mock_hub
            task = asyncio.create_task(
                heartbeat_timeout_checker(storage, interval=999)
            )
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        storage.set_agent_online.assert_called_once_with("stale1", False)
        mock_hub.broadcast.assert_called_once()
