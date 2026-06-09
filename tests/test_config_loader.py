"""Tests for config_loader module."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from agora.coordinator.config_loader import (
    ensure_agora_home,
    expand_path,
    load_default_config,
    load_yaml_config,
    merge_configs,
)


class TestExpandPath:
    def test_expand_tilde(self):
        result = expand_path("~/.agora/data/agora.db")
        assert result.startswith(str(Path.home()))
        assert "~" not in result

    def test_no_tilde(self):
        assert expand_path("/tmp/agora.db") == "/tmp/agora.db"

    def test_relative_path(self):
        assert expand_path("data/agora.db") == "data/agora.db"


class TestMergeConfigs:
    def test_simple_override(self):
        base = {"port": 8765, "host": "0.0.0.0"}
        override = {"port": 9000}
        result = merge_configs(base, override)
        assert result == {"port": 9000, "host": "0.0.0.0"}

    def test_new_key(self):
        base = {"port": 8765}
        override = {"debug": True}
        result = merge_configs(base, override)
        assert result == {"port": 8765, "debug": True}

    def test_nested_dict(self):
        base = {"db": {"path": "a.db", "pool": 5}}
        override = {"db": {"path": "b.db"}}
        result = merge_configs(base, override)
        assert result == {"db": {"path": "b.db", "pool": 5}}

    def test_empty_override(self):
        base = {"port": 8765}
        assert merge_configs(base, {}) == {"port": 8765}


class TestLoadYamlConfig:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_yaml_config(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_loads_valid_yaml(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(yaml.dump({"port": 9000, "debug": True}))
        result = load_yaml_config(cfg)
        assert result == {"port": 9000, "debug": True}

    def test_empty_yaml_returns_empty(self, tmp_path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("")
        result = load_yaml_config(cfg)
        assert result == {}


class TestLoadDefaultConfig:
    def test_default_config_loads(self):
        result = load_default_config()
        assert isinstance(result, dict)
        assert "port" in result
        assert result["port"] == 8765
        assert "db_path" in result
        assert "log_level" in result


class TestEnsureAgoraHome:
    def test_creates_directory(self, tmp_path, monkeypatch):
        import agora.coordinator.config_loader as cl
        test_home = tmp_path / ".agora"
        monkeypatch.setattr(cl, "AGORA_HOME", test_home)
        result = cl.ensure_agora_home()
        assert test_home.exists()
        assert result == test_home
