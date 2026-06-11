"""Tests for Phase 11.1a: Task Query API endpoints."""
from __future__ import annotations

import asyncio

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
    """Create motion + graph, return (motion_id, graph_id)."""
    motion = _run(storage.create_motion(
        title="Test", description="test",
        rounds=3, voting_method="simple_majority", context="",
    ))
    mid = motion["id"]
    gid = "graph-" + mid[:8]
    _run(storage.create_task_graph(gid, mid))
    return mid, gid


def _seed_agent(storage, agent_id="agent-1"):
    """Register an agent for FK constraints on execution_slots."""
    _run(storage.register_agent(
        agent_id=agent_id, name="Test Agent",
        model="test", capabilities=["code"],
        role="participant", agent_type="hermes",
        max_concurrent_tasks=2, agent_token="tok-1",
        is_approved=True, approval_status="approved",
    ))


class TestTaskListEndpoint:
    def test_empty_list(self, client):
        r = client.get("/api/v1/tasks")
        assert r.status_code == 200
        data = r.json()
        assert data["tasks"] == []
        assert data["total"] == 0

    def test_list_with_tasks(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        task = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="Test Task", status=TaskStatus.PENDING,
        )
        _run(storage.create_task(task))
        r = client.get("/api/v1/tasks")
        assert r.status_code == 200
        data = r.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == "t1"

    def test_filter_by_status(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        t1 = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="Pending", status=TaskStatus.PENDING,
        )
        t2 = TaskNode(
            id="t2", graph_id=gid, motion_id=mid,
            title="Running", status=TaskStatus.RUNNING,
        )
        _run(storage.create_task(t1))
        _run(storage.create_task(t2))
        r = client.get("/api/v1/tasks?status=running")
        assert r.status_code == 200
        assert len(r.json()["tasks"]) == 1
        assert r.json()["tasks"][0]["id"] == "t2"


class TestTaskDetailEndpoint:
    def test_not_found(self, client):
        r = client.get("/api/v1/tasks/nonexistent")
        assert r.status_code == 404

    def test_task_detail(self, client, storage):
        mid, gid = _seed_motion_graph(storage)
        task = TaskNode(
            id="t1", graph_id=gid, motion_id=mid,
            title="Detail Task", description="A test",
            status=TaskStatus.RUNNING,
        )
        _run(storage.create_task(task))
        r = client.get("/api/v1/tasks/t1")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "t1"
        assert data["title"] == "Detail Task"
