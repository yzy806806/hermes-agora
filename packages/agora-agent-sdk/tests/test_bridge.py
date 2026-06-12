"""Tests for AbstractBridge — concrete subclass + lifecycle."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora_agent_sdk.bridge import AbstractBridge
from agora_agent_sdk.client import AgoraAgentClient
from agora_agent_sdk.config import AgentConnectionConfig
from agora_agent_sdk.protocol import TaskNode


class ConcreteBridge(AbstractBridge):
    """Test implementation of AbstractBridge."""

    def __init__(self, client: AgoraAgentClient) -> None:
        super().__init__(client)
        self.tasks: list[TaskNode] = []
        self.messages: list[tuple[str, str]] = []
        self.da_responses: list[str] = []

    async def on_task_assigned(self, task: TaskNode) -> None:
        self.tasks.append(task)

    async def on_discussion_message(self, motion_id: str, content: str) -> None:
        self.messages.append((motion_id, content))

    async def on_devils_advocate(self, motion_id: str, topic: str) -> str:
        self.da_responses.append(topic)
        return f"counter-argument for {topic}"


def _make_bridge() -> tuple[AgoraAgentClient, ConcreteBridge]:
    cfg = AgentConnectionConfig(agent_id="b-agent", agent_name="BridgeTest")
    client = AgoraAgentClient(cfg)
    bridge = ConcreteBridge(client)
    client.set_bridge(bridge)
    return client, bridge


@pytest.mark.asyncio
async def test_on_task_assigned():
    _, bridge = _make_bridge()
    task = TaskNode(task_id="t1", title="do stuff")
    await bridge.on_task_assigned(task)
    assert len(bridge.tasks) == 1
    assert bridge.tasks[0].task_id == "t1"


@pytest.mark.asyncio
async def test_on_discussion_message():
    _, bridge = _make_bridge()
    await bridge.on_discussion_message("m1", "hello world")
    assert bridge.messages == [("m1", "hello world")]


@pytest.mark.asyncio
async def test_on_devils_advocate():
    _, bridge = _make_bridge()
    resp = await bridge.on_devils_advocate("m1", "safety")
    assert "safety" in resp
    assert len(bridge.da_responses) == 1


@pytest.mark.asyncio
async def test_lifecycle_start_stop():
    client, bridge = _make_bridge()
    client.register = AsyncMock(return_value=MagicMock(agent_id="b-agent", token="tok"))
    client.connect = AsyncMock()
    client.run = AsyncMock()
    client.disconnect = AsyncMock()
    await bridge.start()
    client.register.assert_called_once()
    client.connect.assert_called_once()
    client.run.assert_called_once()
    await bridge.stop()
    client.disconnect.assert_called_once()
