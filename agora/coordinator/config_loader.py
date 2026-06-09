"""YAML config loader for Agora Coordinator.

Handles loading config from ~/.agora/config.yaml with fallback to defaults.
Creates ~/.agora/ directory on first run if needed.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default config file location
AGORA_HOME = Path.home() / ".agora"
CONFIG_FILE = AGORA_HOME / "config.yaml"


def get_default_config_path() -> Path:
    """Return path to bundled default config.yaml."""
    return Path(__file__).parent / "config_defaults.yaml"


def ensure_agora_home() -> Path:
    """Ensure ~/.agora/ directory exists, create if needed."""
    AGORA_HOME.mkdir(parents=True, exist_ok=True)
    return AGORA_HOME


def load_yaml_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load config from YAML file.
    
    Args:
        config_path: Path to config file. Defaults to ~/.agora/config.yaml.
    
    Returns:
        Dict with config values (empty if file doesn't exist).
    """
    path = config_path or CONFIG_FILE
    if not path.exists():
        logger.debug("Config file not found: %s, using defaults", path)
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        logger.info("Loaded config from %s", path)
        return data


def load_default_config() -> dict[str, Any]:
    """Load bundled default config from config_defaults.yaml."""
    default_path = get_default_config_path()
    if not default_path.exists():
        logger.warning("Default config not found: %s", default_path)
        return {}
    with open(default_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def expand_path(path_str: str) -> str:
    """Expand ~ in path strings to user home directory."""
    if path_str.startswith("~"):
        return str(Path(path_str).expanduser())
    return path_str


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two config dicts, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = {**result[key], **value}
        else:
            result[key] = value
    return result
