"""Tests for AgoraAgentClient — mock HTTP + WebSocket."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from agora_agent_sdk.client import AgoraAgentClient
from agora_agent_sdk.config import AgentConnectionConfig
from agora_agent_sdk.protocol import RegistrationResult


def _config(**kw) -> AgentConnectionConfig:
    defaults = dict(coordinator_url="http://localhost:8765", agent_id="test-agent",
                    agent_name="TestAgent", agent_type="custom",
                    capabilities=["test"], model="test-model")
    defaults.update(kw)
    return AgentConnectionConfig(**defaults)


def _client(**kw) -> AgoraAgentClient:
    return AgoraAgentClient(_config(**kw))


# -- register --


@pytest.mark.asyncio
async def test_register_success():
    client = _client()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"agent_id": "test-agent", "token": "tok123", "agent_token": "tok123"}
    mock_resp.raise_for_status = MagicMock()
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_resp)
    with patch.object(client, "_http", mock_http):
        result = await client.register()
    assert isinstance(result, RegistrationResult)
    assert result.agent_id == "test-agent"


@pytest.mark.asyncio
async def test_register_failure():
    client = _client()
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=httpx.HTTPStatusError(
        "err", request=MagicMock(), response=MagicMock()))
    with patch.object(client, "_http", mock_http):
        with pytest.raises(httpx.HTTPStatusError):
            await client.register()


# -- connect / disconnect --


@pytest.mark.asyncio
async def test_connect_disconnect():
    client = _client()
    mock_ws = AsyncMock()
    with patch("agora_agent_sdk.client_lifecycle.websockets") as ws_mod:
        ws_mod.connect = AsyncMock(return_value=mock_ws)
        with patch("agora_agent_sdk.client_lifecycle.asyncio") as aio_mod:
            aio_mod.create_task = MagicMock(return_value=MagicMock())
            aio_mod.sleep = AsyncMock()
            await client.connect()
    assert client._connected is True
    mock_aclose = AsyncMock()
    with patch.object(client._http, "aclose", mock_aclose):
        await client.disconnect()
    assert client._connected is False


# -- set_bridge --


@pytest.mark.asyncio
async def test_set_bridge():
    client = _client()
    bridge = MagicMock()
    client.set_bridge(bridge)
    assert client._bridge is bridge


# -- run delegates to run_loop --


@pytest.mark.asyncio
async def test_run_delegates():
    client = _client()
    with patch("agora_agent_sdk.client_lifecycle.run_loop", new=AsyncMock()) as mock_run_loop:
        await client.run()
        mock_run_loop.assert_called_once_with(client)