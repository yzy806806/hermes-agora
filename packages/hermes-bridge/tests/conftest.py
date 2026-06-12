"""Shared fixtures for Hermes Bridge integration tests."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agora_agent_sdk import AgoraAgentClient
from agora_agent_sdk.protocol import TaskNode
from agora_hermes_bridge.config import BridgeConfig, ProfileConfig


class MockWS:
    """Mock WebSocket for testing without a real coordinator."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, data: str) -> None:
        import json
        self.sent.append(json.loads(data))

    async def recv(self) -> str:
        await asyncio.sleep(0.01)
        return '{"type":"HEARTBEAT_ACK","payload":{}}'


@pytest.fixture
def profile() -> ProfileConfig:
    return ProfileConfig(
        name="dev-merger",
        capabilities=["coding", "testing"],
        model="astron-code-latest",
    )


@pytest.fixture
def mock_client(profile: ProfileConfig) -> AgoraAgentClient:
    client = MagicMock(spec=AgoraAgentClient)
    client._connected = True
    client._ws = MockWS()
    client._bridge = None
    client.config = MagicMock()
    client.config.coordinator_url = "http://localhost:8765"
    client.config.agent_id = f"hermes-{profile.name}"
    client.report_task_start = AsyncMock()
    client.report_task_complete = AsyncMock()
    client.report_task_failed = AsyncMock()
    return client


@pytest.fixture
def sample_task() -> TaskNode:
    return TaskNode(
        task_id="t_abc123",
        title="Implement feature X",
        description="Build feature X per design doc",
    )


@pytest.fixture
def bridge_config() -> BridgeConfig:
    return BridgeConfig(
        coordinator_url="http://localhost:8765",
        poll_interval=1,
        profiles=[
            ProfileConfig(name="dev-merger", capabilities=["coding"]),
            ProfileConfig(name="reviewer", capabilities=["review"]),
        ],
    )
