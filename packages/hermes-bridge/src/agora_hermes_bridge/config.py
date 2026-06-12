"""Configuration models for Hermes Bridge daemon."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    """Configuration for a single Hermes profile to bridge."""

    name: str
    agent_id: str = ""
    capabilities: list[str] = Field(default_factory=list)
    model: str = "unknown"
    token: str = ""


class BridgeConfig(BaseModel):
    """Top-level configuration for the Hermes Bridge daemon."""

    coordinator_url: str = "http://localhost:8765"
    poll_interval: int = 10
    profiles: list[ProfileConfig] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> BridgeConfig:
        """Load configuration from a YAML file."""
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        return cls(**data)

    def resolve_agent_id(self, profile: ProfileConfig) -> str:
        """Return explicit agent_id or derive from profile name."""
        return profile.agent_id or f"hermes-{profile.name}"
