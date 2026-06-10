"""Tests for Phase 10.2c: Audit logging (audit.py)."""
from __future__ import annotations

import pytest
import aiosqlite

from agora.coordinator.audit import (
    AuditEvent, AuditEventType, AuditLogger,
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


@pytest.fixture
def audit_logger(tmp_path):
    """Create AuditLogger pointing to a temp DB."""
    return AuditLogger(str(tmp_path / "audit.db"))


@pytest.mark.asyncio
class TestAuditEvent:
    async def test_event_creation(self):
        event = AuditEvent(
            event_type=AuditEventType.AUTH,
            actor_id="agent-1",
            actor_role="agent",
            action="login",
            resource="/api/v1/agents",
        )
        assert event.event_type == AuditEventType.AUTH
        assert event.actor_id == "agent-1"
        assert event.action == "login"
        assert event.tenant_id == "default"

    async def test_event_with_details(self):
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION,
            actor_id="admin",
            action="deny",
            resource="/api/v1/tenants",
            details={"reason": "insufficient_role"},
        )
        assert event.details["reason"] == "insufficient_role"


@pytest.mark.asyncio
class TestAuditLogger:
    async def test_log_and_query(self, tmp_path):
        db_path = str(tmp_path / "audit.db")
        # Init schema
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(SCHEMA_SQL)
        logger = AuditLogger(db_path)
        event = AuditEvent(
            event_type=AuditEventType.AGENT,
            actor_id="agent-1",
            actor_role="agent",
            action="register",
            resource="agent-1",
            tenant_id="default",
        )
        row_id = await logger.log_event(event)
        assert row_id > 0

    async def test_query_by_actor(self, tmp_path):
        db_path = str(tmp_path / "audit.db")
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(SCHEMA_SQL)
        logger = AuditLogger(db_path)
        for actor in ["a1", "a2", "a1"]:
            await logger.log_event(AuditEvent(
                event_type=AuditEventType.AUTH,
                actor_id=actor, action="login",
            ))
        results = await logger.query_events(actor_id="a1")
        assert len(results) == 2

    async def test_query_by_action(self, tmp_path):
        db_path = str(tmp_path / "audit.db")
        async with aiosqlite.connect(db_path) as conn:
            await conn.executescript(SCHEMA_SQL)
        logger = AuditLogger(db_path)
        await logger.log_event(AuditEvent(
            event_type=AuditEventType.ADMIN,
            actor_id="admin", action="approve",
        ))
        await logger.log_event(AuditEvent(
            event_type=AuditEventType.ADMIN,
            actor_id="admin", action="delete",
        ))
        results = await logger.query_events(action="approve")
        assert len(results) == 1
        assert results[0]["action"] == "approve"
