"""Tests for agent_client.config module."""

import os

import pytest

from agora.agent_client.config import AgoraConfig, load_config


class TestAgoraConfig:
    """Tests for AgoraConfig dataclass."""

    def test_defaults(self):
        cfg = AgoraConfig()
        assert cfg.coordinator_url == "http://localhost:8765"
        assert cfg.ws_protocol == "ws"
        assert cfg.agent_id == ""
        assert cfg.default_rounds == 3
        assert cfg.default_voting_method == "simple_majority"
        assert cfg.max_retry == 3

    def test_ws_url(self):
        cfg = AgoraConfig(coordinator_url="http://localhost:8765")
        assert cfg.ws_url == "ws://localhost:8765"

    def test_ws_endpoint(self):
        cfg = AgoraConfig(agent_id="agent-1")
        assert cfg.ws_endpoint == "ws://localhost:8765/ws/agent-1"

    def test_ws_endpoint_unknown(self):
        cfg = AgoraConfig(agent_id="")
        assert "unknown" in cfg.ws_endpoint


class TestLoadConfig:
    """Tests for load_config function."""

    def test_empty_config(self):
        cfg = load_config(None)
        assert cfg.coordinator_url == "http://localhost:8765"

    def test_from_hermes_config(self):
        hermes = {"agora": {"coordinator_url": "http://custom:9999", "agent_id": "a1"}}
        cfg = load_config(hermes)
        assert cfg.coordinator_url == "http://custom:9999"
        assert cfg.agent_id == "a1"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("AGORA_COORDINATOR_URL", "http://env:7777")
        cfg = load_config({})
        assert cfg.coordinator_url == "http://env:7777"

    def test_hermes_config_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("AGORA_COORDINATOR_URL", "http://env:7777")
        hermes = {"agora": {"coordinator_url": "http://hermes:5555"}}
        cfg = load_config(hermes)
        assert cfg.coordinator_url == "http://hermes:5555"
