"""Tests for Session and Artifact CRUD (Phase 12.5a)."""

import pytest

from agora.coordinator.storage import Storage


async def _register_agent(storage: Storage, agent_id: str) -> None:
    """Helper: register an agent so FK constraints pass."""
    await storage.register_agent(
        agent_id=agent_id, name=agent_id, model="test")


@pytest.mark.asyncio
async def test_create_and_get_session(storage: Storage):
    await _register_agent(storage, "a1")
    result = await storage.create_session(
        agent_id="a1", project_id="p1")
    sid = result["id"]
    assert result["agent_id"] == "a1"
    assert result["project_id"] == "p1"

    fetched = await storage.get_session(sid)
    assert fetched is not None
    assert fetched["agent_id"] == "a1"


@pytest.mark.asyncio
async def test_get_session_not_found(storage: Storage):
    assert await storage.get_session("nonexistent") is None


@pytest.mark.asyncio
async def test_query_sessions_by_agent(storage: Storage):
    await _register_agent(storage, "a1")
    await _register_agent(storage, "a2")
    r1 = await storage.create_session(agent_id="a1", project_id="p1")
    r2 = await storage.create_session(agent_id="a2", project_id="p1")

    results = await storage.query_sessions(agent_id="a1")
    assert len(results) == 1
    assert results[0]["id"] == r1["id"]


@pytest.mark.asyncio
async def test_update_session(storage: Storage):
    await _register_agent(storage, "a1")
    r = await storage.create_session(agent_id="a1", project_id="p1")
    sid = r["id"]

    updated = await storage.update_session(sid, {"outcome": "failure"})
    assert updated["outcome"] == "failure"


@pytest.mark.asyncio
async def test_add_session_note(storage: Storage):
    await _register_agent(storage, "a1")
    r = await storage.create_session(agent_id="a1", project_id="p1")
    sid = r["id"]
    result = await storage.add_session_note(sid, "a1", "Learned something")
    assert result is not None
    assert len(result["notes"]) == 1
    assert result["notes"][0]["content"] == "Learned something"


@pytest.mark.asyncio
async def test_put_and_get_artifact(storage: Storage):
    result = await storage.put_artifact(
        "p1", "conventions", b"PEP8", "text/plain", "a1")
    assert result["key"] == "conventions"

    art = await storage.get_artifact("p1", "conventions")
    assert art is not None
    assert art["value"] == b"PEP8"


@pytest.mark.asyncio
async def test_put_artifact_upsert(storage: Storage):
    await storage.put_artifact("p1", "k1", b"v1", "text/plain", "a1")
    await storage.put_artifact("p1", "k1", b"v2", "text/plain", "a1")

    art = await storage.get_artifact("p1", "k1")
    assert art["value"] == b"v2"


@pytest.mark.asyncio
async def test_delete_artifact(storage: Storage):
    await storage.put_artifact("p1", "k1", b"v1", "text/plain", "a1")
    assert await storage.delete_artifact("p1", "k1") is True
    assert await storage.get_artifact("p1", "k1") is None
    assert await storage.delete_artifact("p1", "k1") is False


@pytest.mark.asyncio
async def test_list_artifacts(storage: Storage):
    await storage.put_artifact("p1", "k1", b"v1", "text/plain", "a1")
    await storage.put_artifact("p1", "k2", b"v2", "text/plain", "a1")
    arts = await storage.list_artifacts("p1")
    assert len(arts) == 2

    arts_other = await storage.list_artifacts("other")
    assert len(arts_other) == 0
