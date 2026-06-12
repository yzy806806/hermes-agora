"""Tests for Hermes Bridge config and daemon."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agora_hermes_bridge.config import BridgeConfig, ProfileConfig
from agora_hermes_bridge.daemon import HermesBridgeDaemon


class TestBridgeConfig:
    def test_default_config(self):
        cfg = BridgeConfig()
        assert cfg.coordinator_url == "http://localhost:8765"
        assert cfg.profiles == []
        assert cfg.poll_interval == 10

    def test_from_yaml(self, tmp_path: Path):
        yaml_text = """
coordinator_url: http://agora:8000
poll_interval: 5
profiles:
  - name: dev-merger
    capabilities: [coding, testing]
    model: claude-sonnet-4
  - name: reviewer
    agent_id: custom-reviewer-id
"""
        p = tmp_path / "bridge.yaml"
        p.write_text(yaml_text)
        cfg = BridgeConfig.from_yaml(p)
        assert cfg.coordinator_url == "http://agora:8000"
        assert len(cfg.profiles) == 2
        assert cfg.profiles[0].name == "dev-merger"
        assert cfg.profiles[1].agent_id == "custom-reviewer-id"

    def test_resolve_agent_id(self):
        cfg = BridgeConfig()
        p = ProfileConfig(name="planner")
        assert cfg.resolve_agent_id(p) == "hermes-planner"
        p2 = ProfileConfig(name="planner", agent_id="explicit-id")
        assert cfg.resolve_agent_id(p2) == "explicit-id"


class TestHermesBridgeDaemon:
    def test_daemon_creation(self):
        cfg = BridgeConfig(
            profiles=[
                ProfileConfig(name="dev-merger"),
                ProfileConfig(name="reviewer"),
            ]
        )
        daemon = HermesBridgeDaemon(cfg)
        assert len(daemon.adapters) == 0

    @pytest.mark.asyncio
    async def test_daemon_stop(self):
        cfg = BridgeConfig(profiles=[])
        daemon = HermesBridgeDaemon(cfg)
        daemon._running = True
        await daemon.stop()
        assert daemon._running is False

    @pytest.mark.asyncio
    async def test_register_profile(self):
        cfg = BridgeConfig(coordinator_url="http://test:8765")
        daemon = HermesBridgeDaemon(cfg)
        profile = ProfileConfig(name="dev-merger", capabilities=["coding"])
        with patch(
            "agora_hermes_bridge.daemon.HermesAdapter",
            side_effect=RuntimeError("no hermes cli"),
        ):
            with pytest.raises(RuntimeError, match="no hermes cli"):
                await daemon._register_profile(profile)
