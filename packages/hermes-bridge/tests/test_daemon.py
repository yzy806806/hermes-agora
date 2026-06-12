"""Tests for HermesBridgeDaemon — profile registration and lifecycle."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agora_agent_sdk import AgoraAgentClient
from agora_agent_sdk.protocol import TaskNode
from agora_hermes_bridge.config import BridgeConfig, ProfileConfig
from agora_hermes_bridge.daemon import HermesAdapter, HermesBridgeDaemon


class TestDaemonCreation:
    def test_empty_profiles(self):
        cfg = BridgeConfig(profiles=[])
        daemon = HermesBridgeDaemon(cfg)
        assert len(daemon.adapters) == 0
        assert daemon._running is False

    def test_with_profiles(self, bridge_config):
        daemon = HermesBridgeDaemon(bridge_config)
        assert len(daemon.adapters) == 0  # not registered yet


class TestProfileRegistration:
    @pytest.mark.asyncio
    async def test_registers_profiles_as_agents(self, bridge_config):
        daemon = HermesBridgeDaemon(bridge_config)
        with patch(
            "agora_hermes_bridge.daemon.AgoraAgentClient", autospec=True,
        ), patch(
            "agora_hermes_bridge.adapter.hermes_available",
            return_value=True,
        ):
            await daemon._register_profile(bridge_config.profiles[0])
        assert "hermes-dev-merger" in daemon.adapters
        adapter = daemon.adapters["hermes-dev-merger"]
        assert isinstance(adapter, HermesAdapter)
        assert adapter.profile == "dev-merger"

    @pytest.mark.asyncio
    async def test_custom_agent_id(self, bridge_config):
        custom_profile = ProfileConfig(
            name="reviewer", agent_id="my-custom-id",
        )
        daemon = HermesBridgeDaemon(bridge_config)
        with patch(
            "agora_hermes_bridge.daemon.AgoraAgentClient", autospec=True,
        ), patch(
            "agora_hermes_bridge.adapter.hermes_available",
            return_value=True,
        ):
            await daemon._register_profile(custom_profile)
        assert "my-custom-id" in daemon.adapters


class TestDaemonLifecycle:
    @pytest.mark.asyncio
    async def test_stop_sets_running_false(self):
        cfg = BridgeConfig(profiles=[])
        daemon = HermesBridgeDaemon(cfg)
        daemon._running = True
        await daemon.stop()
        assert daemon._running is False

    @pytest.mark.asyncio
    async def test_start_registers_all_profiles(self, bridge_config):
        daemon = HermesBridgeDaemon(bridge_config)
        daemon._register_profile = AsyncMock()
        daemon._run_loop = AsyncMock()
        await daemon.start()
        assert daemon._register_profile.call_count == 2
        assert daemon._running is True

    @pytest.mark.asyncio
    async def test_run_loop_polls(self, bridge_config):
        daemon = HermesBridgeDaemon(bridge_config)
        call_count = 0

        async def fake_loop():
            nonlocal call_count
            call_count += 1
            daemon._running = False

        daemon._run_loop = fake_loop
        daemon._register_profile = AsyncMock()
        await daemon.start()
        assert call_count == 1


class TestDaemonAdapter:
    @pytest.mark.asyncio
    async def test_adapter_on_task_assigned(self, mock_client, profile):
        with patch("agora_hermes_bridge.adapter.hermes_available", return_value=True):
            adapter = HermesAdapter(mock_client, profile.name)
        with patch(
            "agora_hermes_bridge.adapter.run_hermes",
            new_callable=AsyncMock, return_value={"task_id": "kb_001"},
        ), patch(
            "agora_hermes_bridge.adapter.poll_kanban_task",
            new_callable=AsyncMock,
        ):
            task = TaskNode(task_id="t_1", title="Test task")
            await adapter.on_task_assigned(task)
        assert adapter._kanban_map["t_1"] == "kb_001"
