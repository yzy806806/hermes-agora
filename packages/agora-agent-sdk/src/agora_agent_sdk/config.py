"""Configuration for AgoraAgentClient."""

from __future__ import annotations


class AgentConnectionConfig:
    """Configuration for connecting to Agora Coordinator."""

    def __init__(
        self,
        coordinator_url: str = "http://localhost:8765",
        agent_id: str = "",
        agent_name: str = "AgoraAgent",
        agent_type: str = "custom",
        capabilities: list[str] | None = None,
        model: str = "unknown",
        agent_token: str | None = None,
        heartbeat_interval: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.coordinator_url = coordinator_url
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.capabilities = capabilities or []
        self.model = model
        self.agent_token = agent_token
        self.heartbeat_interval = heartbeat_interval
        self.max_retries = max_retries

    @property
    def ws_url(self) -> str:
        host = self.coordinator_url.replace("http://", "").replace(
            "https://", ""
        )
        return f"ws://{host}"

    @property
    def ws_endpoint(self) -> str:
        aid = self.agent_id or "unknown"
        token = self.agent_token or ""
        base = f"{self.ws_url}/ws/{aid}"
        return f"{base}?token={token}" if token else base
