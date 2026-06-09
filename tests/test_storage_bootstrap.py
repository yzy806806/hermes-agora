"""Tests for storage/bootstrap.py CRUD operations."""

import pytest
import pytest_asyncio
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_bootstrap.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest.mark.asyncio(loop_scope="session")
async def test_create_and_get_trigger(storage):
    """create_bootstrap_trigger + get_pending_bootstrap_triggers."""
    tid = await storage.create_bootstrap_trigger(
        "schedule", "topic-1", "cron", "ctx", priority=5,
    )
    assert tid > 0
    pending = await storage.get_pending_bootstrap_triggers()
    assert len(pending) >= 1
    assert pending[0]["topic"] == "topic-1"
    assert pending[0]["priority"] == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_update_trigger_status(storage):
    """update_bootstrap_trigger_status changes status."""
    tid = await storage.create_bootstrap_trigger(
        "event", "topic-2", "api", "ctx2",
    )
    await storage.update_bootstrap_trigger_status(tid, "processed")
    pending = await storage.get_pending_bootstrap_triggers()
    assert all(t["id"] != tid for t in pending)


@pytest.mark.asyncio(loop_scope="session")
async def test_create_and_list_schedule(storage):
    """create_bootstrap_schedule + list_bootstrap_schedules."""
    sid = await storage.create_bootstrap_schedule(
        "daily-check", "0 9 * * *", "Review open issues",
        next_run="2025-01-01T09:00:00",
    )
    assert sid > 0
    schedules = await storage.list_bootstrap_schedules()
    assert len(schedules) >= 1
    assert schedules[0]["name"] == "daily-check"


@pytest.mark.asyncio(loop_scope="session")
async def test_list_schedules_enabled_only(storage):
    """list_bootstrap_schedules with enabled_only filters."""
    await storage.create_bootstrap_schedule(
        "inactive", "0 0 * * *", "Template",
    )
    all_sched = await storage.list_bootstrap_schedules()
    enabled = await storage.list_bootstrap_schedules(enabled_only=True)
    assert len(enabled) <= len(all_sched)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_pending_triggers_limit(storage):
    """get_pending_bootstrap_triggers respects limit."""
    for i in range(5):
        await storage.create_bootstrap_trigger(
            "schedule", f"topic-lim-{i}", "src", "ctx",
        )
    limited = await storage.get_pending_bootstrap_triggers(limit=2)
    assert len(limited) <= 2
