"""Configuration for the Agora agent client.

Reads settings from Hermes config.yaml under the 'agora' key,
with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class AgoraConfig:
    """Agora client configuration."""

    coordinator_url: str = "http://localhost:8765"
    ws_protocol: str = "ws"
    agent_id: str = ""
    agent_name: str = "AgoraAgent"
    default_rounds: int = 3
    default_voting_method: str = "simple_majority"
    connect_timeout: int = 10
    request_timeout: int = 30
    max_retry: int = 3

    @property
    def ws_url(self) -> str:
        """WebSocket base URL derived from coordinator_url."""
        host = self.coordinator_url.replace("http://", "").replace("https://", "")
        return f"{self.ws_protocol}://{host}"

    @property
    def ws_endpoint(self) -> str:
        """Full WebSocket endpoint for this agent."""
        aid = self.agent_id or "unknown"
        return f"{self.ws_url}/ws/{aid}"


def load_config(hermes_config: dict | None = None) -> AgoraConfig:
    """Load AgoraConfig from Hermes config dict + env vars."""
    agora_section = (hermes_config or {}).get("agora", {})
    return AgoraConfig(
        coordinator_url=agora_section.get(
            "coordinator_url", os.getenv("AGORA_COORDINATOR_URL", "http://localhost:8765")
        ),
        ws_protocol=agora_section.get("ws_protocol", "ws"),
        agent_id=agora_section.get("agent_id", os.getenv("AGORA_AGENT_ID", "")),
        agent_name=agora_section.get("agent_name", "AgoraAgent"),
        default_rounds=agora_section.get("default_rounds", 3),
        default_voting_method=agora_section.get(
            "default_voting_method", "simple_majority"
        ),
        connect_timeout=agora_section.get("connect_timeout", 10),
        request_timeout=agora_section.get("request_timeout", 30),
        max_retry=agora_section.get("max_retry", 3),
    )
