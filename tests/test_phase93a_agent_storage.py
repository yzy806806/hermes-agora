"""Tests for Phase 9.3a: Agent storage layer updates."""
from __future__ import annotations

import pytest
import aiosqlite

from agora.coordinator.storage.agents import (
    register_agent,
    get_agent,
    get_agent_by_token,
)
from agora.coordinator.storage.schema import SCHEMA_SQL


@pytest.fixture
async def db(tmp_path):
    """Create an in-memory DB with schema applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    yield conn
    await conn.close()


@pytest.mark.asyncio
class TestRegisterAgent93:
    async def test_register_with_new_fields(self, db):
        result = await register_agent(
            db, "a1", "Agent1", model="gpt-4",
            agent_type="docker", max_concurrent_tasks=5,
            agent_token="ag-test123", is_approved=True,
            approval_status="approved",
        )
        assert result["agent_id"] == "a1"
        assert result["agent_type"] == "docker"
        assert result["max_concurrent_tasks"] == 5
        assert result["agent_token"] == "ag-test123"
        assert result["is_approved"] is True
        assert result["approval_status"] == "approved"
        assert result["load"] == 0.0
        assert result["active_tasks"] == []

    async def test_register_defaults(self, db):
        result = await register_agent(db, "a2", "Agent2")
        assert result["agent_type"] == "hermes"
        assert result["max_concurrent_tasks"] == 2
        assert result["agent_token"] == ""
        assert result["is_approved"] is False
        assert result["approval_status"] == "pending"

    async def test_get_agent_by_token(self, db):
        await register_agent(
            db, "a1", "Agent1",
            agent_token="ag-abc",
        )
        found = await get_agent_by_token(db, "ag-abc")
        assert found is not None
        assert found["agent_id"] == "a1"

    async def test_get_agent_by_token_not_found(self, db):
        found = await get_agent_by_token(db, "nonexistent")
        assert found is None

    async def test_get_agent_has_new_fields(self, db):
        await register_agent(
            db, "a1", "Agent1",
            agent_type="cli", agent_token="ag-xyz",
            is_approved=True, approval_status="approved",
        )
        agent = await get_agent(db, "a1")
        assert agent["agent_type"] == "cli"
        assert agent["agent_token"] == "ag-xyz"
        assert agent["is_approved"] == 1
        assert agent["approval_status"] == "approved"
