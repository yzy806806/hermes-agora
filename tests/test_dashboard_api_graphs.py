"""Tests for Phase 11.1a: Task Graph & Execution Slot endpoints."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agora.coordinator.router import router, init_deps
from agora.coordinator.state import StateMachine
from agora.coordinator.storage import Storage
from agora.coordinator.task_models import (
    ExecutionSlot, TaskNode, TaskStatus,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def storage(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = Storage(db_path)
    _run(s.init_db())
    return s


@pytest.fixture
def app(storage):
    sm = StateMachine(storage)
    init_deps(storage, sm)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _seed_motion_graph(storage):
    motion = _run(storage.create_motion(
        title="Test", description="test",
        rounds=3, voting_method="simple_majority", context="",
    ))
    mid = motion["id"]
    gid = "graph-" + mid[:8]
    _run(storage.create_task_graph(gid, mid))
    return mid, gid


def _seed_agent(storage, agent_id="agent-1"):
    _run(storage.register_agent(
        agent_id=agent_id, name="Test Agent",
        model="test", capabilities=["code"],
        role="participant", agent_type="hermes",
        max_concurrent_tasks=2, agent_token="tok-1",
        is_approved=True, approval_status="approved",
    ))


class TestTaskGraphList:
    def test_empty(self, client):
        r = client.get("/api/v1/task-graphs")
        assert r.status_code == 200
        assert r.json()["graphs"] == []

    def test_list_graphs(self, client, storage):
        _seed_motion_graph(storage)
        _seed_motion_graph(storage)  # second graph
        r = client.get("/api/v1/task-graphs")
        assert r.status_code == 200
        assert len(r.json()["graphs"]) == 2


class TestTaskGraphDetail:
    def test_not_found(self, client):
        r = client.get("/api/v1/task-graphs/nonexistent")
        assert r.status_code == 404

    def test_graph_with_tasks(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        t1 = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="Task 1", status=TaskStatus.DONE,
        )
        t2 = TaskNode(
            id="t2", graph_id=gid, motion_id=mid,
            title="Task 2", status=TaskStatus.PENDING,
        )
        _run(storage.create_task(t1))
        _run(storage.create_task(t2))
        r = client.get(f"/api/v1/task-graphs/{gid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == gid
        assert len(data["tasks"]) == 2


class TestExecutionSlots:
    def test_empty(self, client):
        r = client.get("/api/v1/execution-slots")
        assert r.status_code == 200
        assert r.json()["slots"] == []

    def test_list_slots(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        _seed_agent(storage)
        task = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="Task", status=TaskStatus.RUNNING,
        )
        _run(storage.create_task(task))
        slot = ExecutionSlot(
            task_id="t1", agent_id="agent-1",
            started_at=datetime.now(timezone.utc),
        )
        _run(storage.create_execution_slot(slot))
        r = client.get("/api/v1/execution-slots")
        assert r.status_code == 200
        data = r.json()
        assert len(data["slots"]) == 1
        assert data["slots"][0]["task_id"] == "t1"

    def test_filter_by_agent(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        _seed_agent(storage, "agent-1")
        _seed_agent(storage, "agent-2")
        t1 = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="T1", status=TaskStatus.RUNNING,
        )
        t2 = TaskNode(
            id="t2", graph_id=gid, motion_id=mid,
            title="T2", status=TaskStatus.RUNNING,
        )
        _run(storage.create_task(t1))
        _run(storage.create_task(t2))
        s1 = ExecutionSlot(
            task_id="t1", agent_id="agent-1",
            started_at=datetime.now(timezone.utc),
        )
        s2 = ExecutionSlot(
            task_id="t2", agent_id="agent-2",
            started_at=datetime.now(timezone.utc),
        )
        _run(storage.create_execution_slot(s1))
        _run(storage.create_execution_slot(s2))
        r = client.get("/api/v1/execution-slots?agent_id=agent-1")
        assert r.status_code == 200
        data = r.json()
        assert len(data["slots"]) == 1
        assert data["slots"][0]["agent_id"] == "agent-1"
