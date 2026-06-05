"""Tests for agent_client.client — HTTP tool methods with mocked HTTP."""

import pytest
import httpx

from agent_client.config import AgoraConfig
from agent_client.client import AgoraClient


class MockTransport(httpx.AsyncBaseTransport):
    """Mock HTTP transport that returns preset responses by path."""

    def __init__(self, responses: dict):
        self.responses = responses  # path -> (status, body)
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        # Match by path (strip query string for matching)
        key = request.url.path
        if key in self.responses:
            status, body = self.responses[key]
            return httpx.Response(status, json=body, request=request)
        return httpx.Response(404, json={"detail": "Not found"}, request=request)


def make_client_with_mock(responses: dict, config=None) -> AgoraClient:
    """Create an AgoraClient with a mock HTTP transport."""
    cfg = config or AgoraConfig(
        coordinator_url="http://localhost:8765", agent_id="test-agent"
    )
    client = AgoraClient(cfg)
    transport = MockTransport(responses)
    # Must set base_url so relative paths resolve to full URLs
    client._http = httpx.AsyncClient(
        transport=transport, base_url=cfg.coordinator_url
    )
    return client


class TestCreateMotion:
    @pytest.mark.asyncio
    async def test_success(self):
        mock = {
            "/api/v1/motions": (200, {
                "id": "m1", "title": "Test", "description": "",
                "status": "draft", "rounds": 3,
                "voting_method": "simple_majority",
            }),
        }
        client = make_client_with_mock(mock)
        result = await client.create_motion(title="Test")
        assert result["status"] == "success"
        assert result.get("id") == "m1"

    @pytest.mark.asyncio
    async def test_empty_title(self):
        client = make_client_with_mock({})
        result = await client.create_motion(title="")
        assert result["status"] == "error"
        assert result["error_code"] == "INVALID_PARAMS"

    @pytest.mark.asyncio
    async def test_connection_error(self):
        # No mock responses — transport returns 404
        client = make_client_with_mock({})
        result = await client.create_motion(title="Test")
        assert result["status"] == "error"


class TestListMotions:
    @pytest.mark.asyncio
    async def test_success(self):
        mock = {
            "/api/v1/motions": (200, {
                "motions": [], "total": 0, "limit": 10, "offset": 0,
            }),
        }
        client = make_client_with_mock(mock)
        result = await client.list_motions()
        assert result["status"] == "success"
        assert result["total"] == 0


class TestGetHistory:
    @pytest.mark.asyncio
    async def test_success(self):
        mock = {
            "/api/v1/motions/m1/history": (200, {
                "messages": [], "votes": [],
            }),
        }
        client = make_client_with_mock(mock)
        result = await client.get_history("m1")
        assert result["status"] == "success"
        assert result["motion_id"] == "m1"


class TestGetResult:
    @pytest.mark.asyncio
    async def test_success(self):
        mock = {
            "/api/v1/motions/m1/result": (200, {
                "motion_id": "m1", "decision": "adopted",
                "votes": {"yes": 3, "no": 1},
            }),
        }
        client = make_client_with_mock(mock)
        result = await client.get_result("m1")
        assert result["status"] == "success"
        assert result["decision"] == "adopted"

    @pytest.mark.asyncio
    async def test_not_closed(self):
        mock = {
            "/api/v1/motions/m1/result": (400, {"detail": "Motion not closed yet"}),
        }
        client = make_client_with_mock(mock)
        result = await client.get_result("m1")
        assert result["status"] == "error"
