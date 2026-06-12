"""AgoraAgentClient — main SDK client for connecting agents to Agora.

Provides HTTP + WebSocket lifecycle: register → connect → run event loop.
Discussion and task-reporting methods are bound from client_ws.py.
Lifecycle methods are bound from client_lifecycle.py.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import AgentConnectionConfig
from .protocol import AgentConfig, RegistrationResult
from . import client_ws as _ws_mod
from . import client_lifecycle as _lc_mod

logger = logging.getLogger(__name__)


class AgoraAgentClient:
    """SDK client for an agent to connect to Agora Coordinator."""

    def __init__(self, config: AgentConnectionConfig) -> None:
        self._config = config
        self._http = httpx.AsyncClient(
            base_url=config.coordinator_url, timeout=30.0
        )
        self._ws: Any = None
        self._connected = False
        self._bridge: Any = None
        self._last_ack: float = 0.0
        self._agent_config: AgentConfig | None = None
        self._heartbeat_task: Any = None
        # Bind methods from sibling modules
        self.speak = _ws_mod.speak.__get__(self)
        self.vote = _ws_mod.vote.__get__(self)
        self.report_task_start = _ws_mod.report_task_start.__get__(self)
        self.report_task_progress = _ws_mod.report_task_progress.__get__(self)
        self.report_task_complete = _ws_mod.report_task_complete.__get__(self)
        self.report_task_failed = _ws_mod.report_task_failed.__get__(self)
        self.connect = _lc_mod.connect.__get__(self)
        self.disconnect = _lc_mod.disconnect.__get__(self)
        self.run = _lc_mod.run.__get__(self)

    @property
    def config(self) -> AgentConnectionConfig:
        return self._config

    @property
    def agent_config(self) -> AgentConfig | None:
        return self._agent_config

    def set_bridge(self, bridge: Any) -> None:
        """Set the bridge for dispatching WS events."""
        self._bridge = bridge

    # -- Registration ------------------------------------------------

    async def register(self) -> RegistrationResult:
        """Register this agent with the Coordinator (HTTP POST)."""
        body = {
            "agent_id": self._config.agent_id,
            "name": self._config.agent_name,
            "agent_type": self._config.agent_type,
            "capabilities": self._config.capabilities,
            "model": self._config.model,
        }
        resp = await self._http.post(
            "/api/v1/agents/register", json=body
        )
        resp.raise_for_status()
        data = resp.json()
        self._config.agent_token = data.get("agent_token", "")
        return RegistrationResult(**data)

    async def create_motion(self, title: str, desc: str = "") -> dict:
        """Create a new discussion motion via HTTP."""
        resp = await self._http.post(
            "/api/v1/motions",
            json={"title": title, "description": desc},
        )
        resp.raise_for_status()
        return resp.json()
