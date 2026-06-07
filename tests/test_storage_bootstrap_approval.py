"""Tests for storage/bootstrap_approval.py CRUD operations."""

import pytest
import pytest_asyncio
from coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def storage(tmp_path):
    db_path = str(tmp_path / "test_ba.db")
    s = Storage(db_path)
    await s.init_db()
    yield s


@pytest.mark.asyncio(loop_scope="session")
async def test_create_and_get_approval(storage):
    """create_bootstrap_approval + get_pending_bootstrap_approvals."""
    motion = await storage.create_motion("Test", "Desc")
    mid = motion["id"]
    aid = await storage.create_bootstrap_approval(
        mid, "implement", "Good idea",
        action_items=[{"task": "write code"}],
    )
    assert aid > 0
    pending = await storage.get_pending_bootstrap_approvals()
    assert len(pending) >= 1
    assert pending[0]["motion_id"] == mid


@pytest.mark.asyncio(loop_scope="session")
async def test_decide_approval_approve(storage):
    """decide_bootstrap_approval with approved=True."""
    motion = await storage.create_motion("Test2", "Desc")
    mid = motion["id"]
    aid = await storage.create_bootstrap_approval(
        mid, "deploy", "Ready",
    )
    await storage.decide_bootstrap_approval(
        aid, True, "admin", "LGTM",
    )
    pending = await storage.get_pending_bootstrap_approvals()
    assert all(p["id"] != aid for p in pending)


@pytest.mark.asyncio(loop_scope="session")
async def test_decide_approval_reject(storage):
    """decide_bootstrap_approval with approved=False."""
    motion = await storage.create_motion("Test3", "Desc")
    mid = motion["id"]
    aid = await storage.create_bootstrap_approval(
        mid, "skip", "Not needed",
    )
    await storage.decide_bootstrap_approval(
        aid, False, "admin", "Nope",
    )
    pending = await storage.get_pending_bootstrap_approvals()
    assert all(p["id"] != aid for p in pending)


@pytest.mark.asyncio(loop_scope="session")
async def test_register_and_list_bootstrap_agent(storage):
    """register_bootstrap_agent + list_bootstrap_agents."""
    rid = await storage.register_bootstrap_agent(
        "agent-1", "Planner", "planner", "gpt-4",
        capabilities=["plan", "review"],
    )
    assert rid > 0
    agents = await storage.list_bootstrap_agents()
    assert len(agents) >= 1
    assert agents[0]["agent_id"] == "agent-1"


@pytest.mark.asyncio(loop_scope="session")
async def test_list_bootstrap_agents_active_only(storage):
    """list_bootstrap_agents with active_only filters."""
    await storage.register_bootstrap_agent(
        "agent-2", "Worker", "worker", "claude",
    )
    all_agents = await storage.list_bootstrap_agents()
    active = await storage.list_bootstrap_agents(active_only=True)
    assert len(active) <= len(all_agents)


@pytest.mark.asyncio(loop_scope="session")
async def test_get_pending_approvals_limit(storage):
    """get_pending_bootstrap_approvals respects limit."""
    for i in range(5):
        motion = await storage.create_motion(f"TestLim{i}", "Desc")
        await storage.create_bootstrap_approval(
            motion["id"], "decide", "Reason",
        )
    limited = await storage.get_pending_bootstrap_approvals(limit=2)
    assert len(limited) <= 2
