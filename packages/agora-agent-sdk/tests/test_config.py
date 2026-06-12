"""Tests for config.py — AgentConnectionConfig."""

from agora_agent_sdk.config import AgentConnectionConfig


class TestAgentConnectionConfig:
    def test_defaults(self):
        cfg = AgentConnectionConfig(agent_id="a1")
        assert cfg.coordinator_url == "http://localhost:8765"
        assert cfg.agent_id == "a1"
        assert cfg.agent_type == "custom"
        assert cfg.heartbeat_interval == 30
        assert cfg.max_retries == 3

    def test_ws_url(self):
        cfg = AgentConnectionConfig(
            coordinator_url="http://myhost:8000",
            agent_id="agent-1",
        )
        assert cfg.ws_url == "ws://myhost:8000"

    def test_ws_endpoint_with_token(self):
        cfg = AgentConnectionConfig(
            coordinator_url="http://myhost:8000",
            agent_id="agent-1",
            agent_token="tok-abc",
        )
        ep = cfg.ws_endpoint
        assert "agent-1" in ep
        assert "tok-abc" in ep

    def test_ws_endpoint_without_token(self):
        cfg = AgentConnectionConfig(
            coordinator_url="http://myhost:8000",
            agent_id="agent-1",
        )
        ep = cfg.ws_endpoint
        assert "?token=" not in ep