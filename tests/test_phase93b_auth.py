"""Tests for Phase 9.3b: Registration Auth (token-based WS auth + approval flow)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agora.coordinator.models import AgentStatus
from agora.coordinator.router import init_deps, router
from agora.coordinator.state import StateMachine


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_agent = AsyncMock(return_value=None)
    s.register_agent = AsyncMock(return_value={
        "agent_id": "a1", "name": "Test", "model": "gpt-4",
        "agent_type": "hermes", "max_concurrent_tasks": 2,
        "agent_token": "ag-testtoken", "is_approved": 1,
        "approval_status": "approved", "capabilities": [],
        "role": "participant", "registered_at": "2026-01-01T00:00:00",
        "is_online": False, "last_seen": None,
    })
    s.set_agent_approval = AsyncMock()
    s.list_agents = AsyncMock(return_value=[])
    s.deregister_agent = AsyncMock()
    return s


@pytest.fixture
def mock_sm():
    return AsyncMock(spec=StateMachine)


@pytest.fixture
def client(mock_storage, mock_sm):
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    init_deps(mock_storage, mock_sm)
    return TestClient(app, raise_server_exceptions=False)


class TestRegisterWithApproval:
    def test_register_auto_approve(self, client, mock_storage):
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.require_approval = False
            resp = client.post("/agents/register", json={
                "agent_id": "a1", "name": "Test", "model": "gpt-4",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "approved"
        assert data["agent_token"].startswith("ag-")

    def test_register_pending_approval(self, client, mock_storage):
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.require_approval = True
            resp = client.post("/agents/register", json={
                "agent_id": "a1", "name": "Test", "model": "gpt-4",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert "pending approval" in data["message"]


class TestAdminEndpoints:
    def test_approve_no_admin_token(self, client, mock_storage):
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = ""
            resp = client.post("/admin/agents/a1/approve")
        assert resp.status_code == 501

    def test_approve_wrong_token(self, client, mock_storage):
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = "sk-admin-correct"
            resp = client.post("/admin/agents/a1/approve",
                               headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401

    def test_approve_agent(self, client, mock_storage):
        mock_storage.get_agent = AsyncMock(return_value={"agent_id": "a1"})
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = "sk-admin-test"
            resp = client.post("/admin/agents/a1/approve",
                               headers={"Authorization": "Bearer sk-admin-test"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

    def test_reject_agent(self, client, mock_storage):
        mock_storage.get_agent = AsyncMock(return_value={"agent_id": "a1"})
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = "sk-admin-test"
            resp = client.post("/admin/agents/a1/reject",
                               headers={"Authorization": "Bearer sk-admin-test"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_suspend_agent(self, client, mock_storage):
        mock_storage.get_agent = AsyncMock(return_value={"agent_id": "a1"})
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = "sk-admin-test"
            resp = client.post("/admin/agents/a1/suspend",
                               headers={"Authorization": "Bearer sk-admin-test"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "suspended"

    def test_approve_not_found(self, client, mock_storage):
        with patch("agora.coordinator.router.settings") as mock_s:
            mock_s.admin_token = "sk-admin-test"
            resp = client.post("/admin/agents/unknown/approve",
                               headers={"Authorization": "Bearer sk-admin-test"})
        assert resp.status_code == 404
