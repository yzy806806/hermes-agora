"""Tests for config.py - Settings with YAML + env var priority."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from agora.coordinator.config import Settings, load_settings


class TestSettingsDefaults:
    def test_default_values(self):
        s = Settings()
        assert s.port == 8765
        assert s.host == "0.0.0.0"
        assert s.debug is False
        assert s.log_level == "INFO"
        assert s.require_api_key is False
        assert s.heartbeat_interval_seconds == 30

    def test_db_path_default_is_under_home(self):
        s = Settings()
        assert ".agora" in s.db_path
        assert "agora.db" in s.db_path


class TestEnvOverride:
    def test_env_overrides_default(self, monkeypatch):
        monkeypatch.setenv("AGORA_PORT", "9000")
        s = Settings()
        assert s.port == 9000

    def test_env_overrides_yaml_defaults(self, monkeypatch):
        """Env vars override YAML-provided defaults in load_settings."""
        monkeypatch.setenv("AGORA_PORT", "7777")
        s = load_settings()
        assert s.port == 7777

    def test_env_bool_override(self, monkeypatch):
        monkeypatch.setenv("AGORA_DEBUG", "true")
        s = Settings()
        assert s.debug is True

    def test_env_string_override(self, monkeypatch):
        monkeypatch.setenv("AGORA_LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"


class TestYamlIntegration:
    def test_yaml_values_via_load_settings(self, tmp_path, monkeypatch):
        """load_settings reads YAML and uses values as defaults."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"port": 9000}))
        # Patch load_yaml_config to return our test data
        with patch("agora.coordinator.config.load_yaml_config", return_value={"port": 9000}):
            monkeypatch.delenv("AGORA_PORT", raising=False)
            s = load_settings()
            assert s.port == 9000

    def test_yaml_db_path_expanded(self):
        home_db = str(Path.home() / ".agora" / "data" / "agora.db")
        s = Settings(db_path=home_db)
        assert "~" not in s.db_path


class TestConfigPriority:
    """Priority: CLI > env vars > config.yaml > defaults."""

    def test_cli_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("AGORA_PORT", "5555")
        s = load_settings(port=9999)  # CLI override
        assert s.port == 9999

    def test_env_wins_over_yaml(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AGORA_PORT", "5555")
        with patch("agora.coordinator.config.load_yaml_config", return_value={"port": 9000}):
            s = load_settings()
            assert s.port == 5555
