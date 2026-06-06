"""Tests for trigger_types and TriggerManager."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
import pytest_asyncio

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coordinator.bootstrap.trigger_types import TriggerEvent, TriggerType
from coordinator.bootstrap.trigger_manager import TriggerManager
from coordinator.storage.schema import SCHEMA_SQL


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(loop_scope="module")
async def db(tmp_path_factory):
    """Create an in-memory DB with bootstrap schema."""
    import aiosqlite
    db_path = str(tmp_path_factory.mktemp("bootstrap") / "test.db")
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    yield db_path


@pytest_asyncio.fixture(loop_scope="module")
async def mgr(db):
    return TriggerManager(db)


class TestTriggerType:
    def test_values(self):
        assert TriggerType.SCHEDULED.value == "scheduled"
        assert TriggerType.USER_REQUESTED.value == "user_requested"
        assert TriggerType.GITHUB_ISSUE.value == "github_issue"
        assert TriggerType.ROADMAP_CHANGE.value == "roadmap_change"

    def test_from_string(self):
        assert TriggerType("scheduled") is TriggerType.SCHEDULED


class TestTriggerEvent:
    def test_creation(self):
        evt = TriggerEvent(
            trigger_type=TriggerType.USER_REQUESTED,
            topic="test topic", source="user1",
            context="some context", priority=5,
        )
        assert evt.trigger_type is TriggerType.USER_REQUESTED
        assert evt.topic == "test topic"
        assert evt.priority == 5
        assert evt.created_at is not None

    def test_default_priority(self):
        evt = TriggerEvent(
            trigger_type=TriggerType.SCHEDULED,
            topic="x", source="cron", context="",
        )
        assert evt.priority == 0

    def test_to_dict(self):
        evt = TriggerEvent(
            trigger_type=TriggerType.GITHUB_ISSUE,
            topic="bug", source="#42", context="desc",
        )
        d = evt.to_dict()
        assert d["trigger_type"] == "github_issue"
        assert d["source"] == "#42"
        assert "created_at" in d


class TestTriggerManager:
    @pytest.mark.asyncio
    async def test_create_trigger(self, mgr):
        tid = await mgr.create_trigger(
            trigger_type=TriggerType.USER_REQUESTED,
            topic="new feature", source="alice",
            context="need auth", priority=3,
        )
        assert tid.isdigit()

    @pytest.mark.asyncio
    async def test_get_trigger(self, mgr):
        tid = await mgr.create_trigger(
            trigger_type=TriggerType.SCHEDULED,
            topic="weekly sync", source="cron",
            context="", priority=1,
        )
        row = await mgr.get_trigger(tid)
        assert row is not None
        assert row["topic"] == "weekly sync"
        assert row["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_pending_triggers(self, mgr):
        await mgr.create_trigger(
            TriggerType.USER_REQUESTED, "t1", "u1", "c1", 1,
        )
        await mgr.create_trigger(
            TriggerType.USER_REQUESTED, "t2", "u2", "c2", 5,
        )
        pending = await mgr.get_pending_triggers(limit=10)
        assert len(pending) >= 2
        # Higher priority first
        topics = [p["topic"] for p in pending]
        assert "t2" in topics

    @pytest.mark.asyncio
    async def test_mark_processed(self, mgr):
        tid = await mgr.create_trigger(
            TriggerType.GITHUB_ISSUE, "bug", "#1", "fix it",
        )
        await mgr.mark_processed(tid)
        row = await mgr.get_trigger(tid)
        assert row["status"] == "processed"
        assert row["processed_at"] is not None

    @pytest.mark.asyncio
    async def test_mark_failed(self, mgr):
        tid = await mgr.create_trigger(
            TriggerType.ROADMAP_CHANGE, "change", "roadmap", "update",
        )
        await mgr.mark_failed(tid)
        row = await mgr.get_trigger(tid)
        assert row["status"] == "failed"

    @pytest.mark.asyncio
    async def test_get_trigger_not_found(self, mgr):
        row = await mgr.get_trigger("999999")
        assert row is None
