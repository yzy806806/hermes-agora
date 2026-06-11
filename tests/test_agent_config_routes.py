"""Tests for Phase 11.1b: Agent config & token rotation endpoints."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agora.coordinator.agent_config_routes import (
    router, init_agent_config_deps,
)
from agora.coordinator.state import StateMachine
from agora.coordinator.storage import Storage
from agora.coordinator.token_manager import TokenManager


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
    tm = TokenManager(secret="test-secret")
    init_agent_config_deps(storage, tm)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def _seed_agent(storage, agent_id="agent-1"):
    _run(storage.register_agent(
        agent_id=agent_id, name="Test Agent",
        model="test", capabilities=["code"],
        role="participant", agent_type="hermes",
        max_concurrent_tasks=2, agent_token="tok-1",
        is_approved=True, approval_status="approved",
    ))


class TestUpdateAgentConfig:
    def test_agent_not_found(self, client):
        r = client.put("/api/v1/admin/agents/no-such/config", json={})
        assert r.status_code == 404

    def test_update_tpm_limit(self, client, storage):
        _seed_agent(storage)
        r = client.put(
            "/api/v1/admin/agents/agent-1/config",
            json={"tpm_limit": 20000},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["agent_id"] == "agent-1"
        assert data["tpm_limit"] == 20000

    def test_update_multiple_fields(self, client, storage):
        _seed_agent(storage)
        r = client.put(
            "/api/v1/admin/agents/agent-1/config",
            json={
                "tpm_limit": 5000,
                "max_concurrent_tasks": 5,
                "role": "expert",
                "allowed_discussion_roles": ["participant", "reviewer"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tpm_limit"] == 5000
        assert data["max_concurrent_tasks"] == 5
        assert data["role"] == "expert"
        assert data["allowed_discussion_roles"] == ["participant", "reviewer"]

    def test_empty_body_no_change(self, client, storage):
        _seed_agent(storage)
        r = client.put(
            "/api/v1/admin/agents/agent-1/config", json={},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tpm_limit"] == 10000


class TestRotateAgentToken:
    def test_agent_not_found(self, client):
        r = client.post("/api/v1/admin/agents/no-such/token")
        assert r.status_code == 404

    def test_rotate_token(self, client, storage):
        _seed_agent(storage)
        r = client.post("/api/v1/admin/agents/agent-1/token")
        assert r.status_code == 200
        data = r.json()
        assert data["agent_id"] == "agent-1"
        assert data["agent_token"].startswith("ag-")
        assert data["agent_token"] != "tok-1"

    def test_rotate_twice_different(self, client, storage):
        _seed_agent(storage)
        r1 = client.post("/api/v1/admin/agents/agent-1/token")
        r2 = client.post("/api/v1/admin/agents/agent-1/token")
        assert r1.json()["agent_token"] != r2.json()["agent_token"]
