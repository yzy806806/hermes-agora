"""Tests for AgoraAgentClient — discussion + task WS methods."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora_agent_sdk.client import AgoraAgentClient
from agora_agent_sdk.config import AgentConnectionConfig


def _client() -> AgoraAgentClient:
    cfg = AgentConnectionConfig(agent_id="ws-agent", agent_name="WS Test")
    return AgoraAgentClient(cfg)


def _connected_client() -> AgoraAgentClient:
    client = _client()
    client._ws = AsyncMock()
    client._connected = True
    return client


@pytest.mark.asyncio
async def test_create_motion():
    client = _client()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"motion_id": "m1", "status": "ok"}
    mock_resp.raise_for_status = MagicMock()
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)
    from unittest.mock import patch
    with patch.object(client, "_http", mock_http):
        result = await client.create_motion("Test Motion", "desc")
    assert result["motion_id"] == "m1"


@pytest.mark.asyncio
async def test_speak():
    client = _connected_client()
    await client.speak("m1", "hello")
    msg = client._ws.send.call_args[0][0]
    assert "SPEAK" in msg


@pytest.mark.asyncio
async def test_vote():
    client = _connected_client()
    await client.vote("m1", "agree")
    msg = client._ws.send.call_args[0][0]
    assert "VOTE" in msg


@pytest.mark.asyncio
async def test_report_task_start():
    client = _connected_client()
    await client.report_task_start("t1")
    msg = client._ws.send.call_args[0][0]
    assert "TASK_STARTED" in msg


@pytest.mark.asyncio
async def test_report_task_progress():
    client = _connected_client()
    await client.report_task_progress("t1", 0.5)
    msg = client._ws.send.call_args[0][0]
    assert "TASK_PROGRESS" in msg
    assert "0.5" in msg


@pytest.mark.asyncio
async def test_report_task_complete():
    client = _connected_client()
    await client.report_task_complete("t1", ["artifact.txt"])
    msg = client._ws.send.call_args[0][0]
    assert "TASK_COMPLETED" in msg


@pytest.mark.asyncio
async def test_report_task_failed():
    client = _connected_client()
    await client.report_task_failed("t1", "timeout")
    msg = client._ws.send.call_args[0][0]
    assert "TASK_FAILED" in msg
