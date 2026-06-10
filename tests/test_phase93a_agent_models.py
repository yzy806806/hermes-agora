"""Tests for Phase 9.3a: Agent Model Updates."""
from __future__ import annotations

import pytest

from agora.coordinator.models import (
    AgentConfig,
    AgentInfo,
    AgentRegisterRequest,
    AgentRegistrationResponse,
    AgentStatus,
    AgentType,
)


class TestAgentTypeEnum:
    def test_values(self):
        assert AgentType.HERMES.value == "hermes"
        assert AgentType.DOCKER.value == "docker"
        assert AgentType.CLI.value == "cli"
        assert AgentType.CUSTOM.value == "custom"

    def test_from_str(self):
        assert AgentType("docker") == AgentType.DOCKER


class TestAgentStatusEnum:
    def test_values(self):
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.APPROVED.value == "approved"
        assert AgentStatus.REJECTED.value == "rejected"
        assert AgentStatus.SUSPENDED.value == "suspended"


class TestAgentRegisterRequest:
    def test_defaults(self):
        req = AgentRegisterRequest(agent_id="a1", name="Test")
        assert req.agent_type == AgentType.HERMES
        assert req.model == "unknown"
        assert req.max_concurrent_tasks == 2
        assert req.auth_token == ""

    def test_custom(self):
        req = AgentRegisterRequest(
            agent_id="a1", name="Test",
            agent_type=AgentType.DOCKER,
            model="gpt-4", max_concurrent_tasks=5,
        )
        assert req.agent_type == AgentType.DOCKER
        assert req.max_concurrent_tasks == 5


class TestAgentInfo:
    def test_new_fields_default(self):
        info = AgentInfo(agent_id="a1", name="Test")
        assert info.agent_type == AgentType.HERMES
        assert info.agent_token == ""
        assert info.is_approved is False
        assert info.approval_status == AgentStatus.PENDING
        assert info.load == 0.0
        assert info.active_tasks == []

    def test_new_fields_set(self):
        info = AgentInfo(
            agent_id="a1", name="Test",
            agent_type=AgentType.CLI,
            agent_token="ag-abc",
            is_approved=True,
            approval_status=AgentStatus.APPROVED,
            load=0.75,
            active_tasks=["t1", "t2"],
        )
        assert info.agent_type == AgentType.CLI
        assert info.is_approved is True
        assert info.load == 0.75


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.max_concurrent_tasks == 2
        assert cfg.heartbeat_interval_seconds == 30
        assert cfg.tpm_limit == 10000
        assert cfg.auto_accept_tasks is False


class TestAgentRegistrationResponse:
    def test_fields(self):
        resp = AgentRegistrationResponse(
            agent_id="a1",
            status=AgentStatus.APPROVED,
            agent_token="ag-abc123",
            message="OK",
        )
        assert resp.status == AgentStatus.APPROVED
        assert resp.agent_token == "ag-abc123"
