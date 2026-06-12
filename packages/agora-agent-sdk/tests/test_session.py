"""Tests for SessionStore and session models (HTTP-backed store)."""

import pytest
import httpx

from agora_agent_sdk.models import SessionRecord, SessionFilter, SessionNote
from agora_agent_sdk.session import SessionStore


# -- Model tests --


class TestSessionRecord:
    def test_defaults(self):
        rec = SessionRecord(agent_id="agent-1")
        assert rec.agent_id == "agent-1"
        assert rec.session_type == "task_execution"
        assert rec.outcome == "success"
        assert rec.input_messages == []
        assert rec.id

    def test_full_construction(self):
        rec = SessionRecord(
            id="s-001",
            agent_id="agent-1",
            project_id="proj-1",
            session_type="discussion",
            outcome="failure",
            errors=[{"code": "TIMEOUT"}],
            metadata={"key": "val"},
        )
        assert rec.project_id == "proj-1"
        assert rec.errors == [{"code": "TIMEOUT"}]

    def test_serialization_roundtrip(self):
        rec = SessionRecord(agent_id="a1", project_id="p1")
        data = rec.model_dump(mode="json")
        rec2 = SessionRecord(**data)
        assert rec2.agent_id == "a1"
        assert rec2.id == rec.id


class TestSessionFilter:
    def test_defaults(self):
        f = SessionFilter()
        assert f.limit == 20
        assert f.agent_id is None

    def test_custom(self):
        f = SessionFilter(agent_id="a1", limit=50, outcome="failure")
        assert f.agent_id == "a1"
        assert f.outcome == "failure"

    def test_exclude_none(self):
        f = SessionFilter(agent_id="a1")
        d = f.model_dump(exclude_none=True)
        assert "project_id" not in d
        assert d["agent_id"] == "a1"


class TestSessionNote:
    def test_basic(self):
        note = SessionNote(content="learned something", tags=["insight"])
        assert note.content == "learned something"
        assert note.tags == ["insight"]


# -- SessionStore HTTP tests (mocked) --


BASE = "http://testserver"


def _mock_client(handler):
    """Create an AsyncClient with MockTransport and base_url."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url=BASE)


class TestSessionStoreRecord:
    @pytest.mark.asyncio
    async def test_record_session(self):
        session = SessionRecord(agent_id="test-agent", project_id="p1")

        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            return httpx.Response(201, json={"status": "ok"})

        store = SessionStore(BASE, "test-agent")
        store._client = lambda: _mock_client(handler)
        await store.record_session(session)


class TestSessionStoreQuery:
    @pytest.mark.asyncio
    async def test_query_sessions(self):
        sessions_data = [
            {"id": "s1", "agent_id": "a1", "outcome": "success"},
            {"id": "s2", "agent_id": "a1", "outcome": "failure"},
        ]

        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={"sessions": sessions_data})

        store = SessionStore(BASE, "a1")
        store._client = lambda: _mock_client(handler)
        results = await store.query_sessions(agent_id="a1")
        assert len(results) == 2
        assert results[0].id == "s1"

    @pytest.mark.asyncio
    async def test_query_sessions_list_response(self):
        sessions_data = [{"id": "s1", "agent_id": "a1", "outcome": "success"}]

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=sessions_data)

        store = SessionStore(BASE, "a1")
        store._client = lambda: _mock_client(handler)
        results = await store.query_sessions()
        assert len(results) == 1


class TestSessionStoreGet:
    @pytest.mark.asyncio
    async def test_get_session(self):
        data = {"id": "s1", "agent_id": "a1", "outcome": "success"}

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=data)

        store = SessionStore(BASE, "a1")
        store._client = lambda: _mock_client(handler)
        result = await store.get_session("s1")
        assert result is not None
        assert result.id == "s1"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        store = SessionStore(BASE, "a1")
        store._client = lambda: _mock_client(handler)
        result = await store.get_session("nonexistent")
        assert result is None


class TestSessionStoreNote:
    @pytest.mark.asyncio
    async def test_add_note(self):
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            return httpx.Response(201, json={"status": "ok"})

        store = SessionStore(BASE, "a1")
        store._client = lambda: _mock_client(handler)
        note = SessionNote(content="key finding", tags=["insight"])
        await store.add_note("s1", note)
