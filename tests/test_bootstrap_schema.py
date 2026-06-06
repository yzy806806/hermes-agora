"""Tests for bootstrap DB schema and schedule_checker."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coordinator.storage.schema import SCHEMA_SQL
from coordinator.bootstrap.schedule_checker import (
    check_scheduled_triggers,
    update_schedule_run,
)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(loop_scope="module")
async def db_path(tmp_path_factory):
    """Create a temp DB with full schema."""
    import aiosqlite
    path = str(tmp_path_factory.mktemp("schema") / "test.db")
    async with aiosqlite.connect(path) as conn:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    yield path


class TestBootstrapSchema:
    @pytest.mark.asyncio
    async def test_bootstrap_triggers_table(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_triggers
                   (trigger_type, topic, source, context,
                    priority, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ["user_requested", "test", "u1", "ctx", 0,
                 "pending", "2026-01-01T00:00:00"],
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM bootstrap_triggers"
            ) as cur:
                rows = list(await cur.fetchall())
                assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_bootstrap_schedules_table(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_schedules
                   (name, cron_expression, topic_template, enabled)
                   VALUES (?, ?, ?, ?)""",
                ["daily", "0 9 * * *", "Daily sync", 1],
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM bootstrap_schedules"
            ) as cur:
                rows = list(await cur.fetchall())
                assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_bootstrap_approvals_table(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_approvals
                   (motion_id, decision, rationale, action_items,
                    approval_status, requested_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ["m1", "adopted", "good", "[]",
                 "pending", "2026-01-01T00:00:00"],
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM bootstrap_approvals"
            ) as cur:
                rows = list(await cur.fetchall())
                assert len(rows) == 1


class TestScheduleChecker:
    @pytest.mark.asyncio
    async def test_check_scheduled_triggers_empty(self, db_path):
        triggers = await check_scheduled_triggers(db_path)
        assert triggers == []

    @pytest.mark.asyncio
    async def test_check_scheduled_triggers_due(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_schedules
                   (name, cron_expression, topic_template,
                    enabled, next_run)
                   VALUES (?, ?, ?, ?, ?)""",
                ["test_due", "0 9 * * *", "Test", 1,
                 "2000-01-01T00:00:00"],
            )
            await db.commit()
        triggers = await check_scheduled_triggers(db_path)
        assert len(triggers) >= 1
        names = [t["name"] for t in triggers]
        assert "test_due" in names

    @pytest.mark.asyncio
    async def test_update_schedule_run(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                """INSERT INTO bootstrap_schedules
                   (name, cron_expression, topic_template, enabled)
                   VALUES (?, ?, ?, ?)""",
                ["upd_test", "0 9 * * *", "Upd", 1],
            )
            await db.commit()
            sid = cursor.lastrowid
        await update_schedule_run(
            db_path, sid,
            "2026-01-01T09:00:00", "2026-01-02T09:00:00",
        )
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bootstrap_schedules WHERE id = ?",
                [sid],
            ) as cur:
                row = dict(await cur.fetchone())
                assert row["last_run"] == "2026-01-01T09:00:00"
                assert row["next_run"] == "2026-01-02T09:00:00"


class TestBootstrapAgents:
    @pytest.mark.asyncio
    async def test_bootstrap_agents_table(self, db_path):
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """INSERT INTO bootstrap_agents
                   (agent_id, name, role, model, capabilities)
                   VALUES (?, ?, ?, ?, ?)""",
                ["dev1", "Developer", "developer", "gpt-4", "[]"],
            )
            await db.commit()
            async with db.execute(
                "SELECT * FROM bootstrap_agents"
            ) as cur:
                rows = list(await cur.fetchall())
                assert len(rows) == 1
