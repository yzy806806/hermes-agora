"""Tests for Phase 10.2e: RBAC Storage + Migration."""
from __future__ import annotations

import pytest
import aiosqlite

from agora.coordinator.storage.rbac import (
    create_token, get_token_by_hash, revoke_token,
    get_role, list_roles, seed_default_roles,
    log_audit, query_audit,
)
from agora.coordinator.storage.schema import SCHEMA_SQL, DEFAULT_ROLES


@pytest.fixture
async def db(tmp_path):
    """In-memory DB with RBAC tables created."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await seed_default_roles(conn)
    yield conn
    await conn.close()


class TestSeedDefaultRoles:
    async def test_seeds_three_roles(self, db) -> None:
        roles = await list_roles(db)
        names = {r["name"] for r in roles}
        assert names == {"admin", "agent", "observer"}

    async def test_idempotent(self, db) -> None:
        await seed_default_roles(db)
        roles = await list_roles(db)
        assert len(roles) == 3


class TestGetRole:
    async def test_existing_role(self, db) -> None:
        role = await get_role(db, "admin")
        assert role is not None
        assert role["name"] == "admin"
        assert "agent:approve" in role["permissions"]

    async def test_missing_role(self, db) -> None:
        role = await get_role(db, "nonexistent")
        assert role is None


class TestTokenCRUD:
    async def test_create_and_lookup(self, db) -> None:
        tok = await create_token(
            db, "agent-1", "agent", "hash123", "tid-1")
        assert tok["principal_id"] == "agent-1"
        found = await get_token_by_hash(db, "hash123")
        assert found is not None
        assert found["principal_id"] == "agent-1"

    async def test_revoke_token(self, db) -> None:
        tok = await create_token(
            db, "agent-2", "observer", "hash456", "tid-2")
        # Look up row id via hash
        row = await get_token_by_hash(db, "hash456")
        assert row is not None
        await revoke_token(db, row["id"])
        found = await get_token_by_hash(db, "hash456")
        assert found is None

    async def test_unknown_hash(self, db) -> None:
        found = await get_token_by_hash(db, "nope")
        assert found is None


class TestAuditLog:
    async def test_log_and_query(self, db) -> None:
        aid = await log_audit(
            db, "auth", "user-1", "login", resource="/api",
            actor_role="admin", details={"ip": "1.2.3.4"})
        assert aid > 0
        rows = await query_audit(db)
        assert len(rows) == 1
        assert rows[0]["actor_id"] == "user-1"

    async def test_filter_by_actor(self, db) -> None:
        await log_audit(db, "auth", "user-1", "login")
        await log_audit(db, "auth", "user-2", "login")
        rows = await query_audit(db, actor_id="user-2")
        assert len(rows) == 1

    async def test_filter_by_event_type(self, db) -> None:
        await log_audit(db, "auth", "u1", "login")
        await log_audit(db, "task", "u1", "execute")
        rows = await query_audit(db, event_type="task")
        assert len(rows) == 1
