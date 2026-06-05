"""WebSocket connection manager for the Agora Coordinator service.

Provides ConnectionManager for connection lifecycle management.
Endpoint and handlers live in ws_endpoint.py and ws_handlers.py.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from .state import StateMachine
    from .storage import Storage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections by agent_id."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self._storage: Optional[Storage] = None
        self._state_machine: Optional[StateMachine] = None

    def set_deps(self, storage: Storage, sm: StateMachine) -> None:
        """Inject storage and state machine dependencies."""
        self._storage = storage
        self._state_machine = sm

    async def connect(self, agent_id: str, websocket: WebSocket) -> bool:
        """Accept WS and mark agent online. Returns False if not registered."""
        if self._storage is None:
            await websocket.close(code=1011, reason="Not initialized")
            return False
        agent = await self._storage.get_agent(agent_id)
        if agent is None:
            await websocket.close(code=4004, reason="Not registered")
            return False
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        await self._storage.set_agent_online(agent_id, True)
        logger.info("Agent %s connected via WebSocket", agent_id)
        return True

    def disconnect(self, agent_id: str) -> None:
        """Remove a WebSocket connection."""
        self.active_connections.pop(agent_id, None)
        logger.info("Agent %s disconnected from WebSocket", agent_id)

    async def send(self, agent_id: str, message: dict[str, Any]) -> bool:
        """Send a JSON message to a specific agent."""
        ws = self.active_connections.get(agent_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            logger.warning("Send failed to agent %s", agent_id)
            return False

    async def broadcast(
        self, message: dict[str, Any], exclude: list[str] | None = None
    ) -> int:
        """Broadcast a JSON message to all connected agents."""
        exclude_set = set(exclude or [])
        count = 0
        for aid, ws in list(self.active_connections.items()):
            if aid not in exclude_set:
                try:
                    await ws.send_json(message)
                    count += 1
                except Exception:
                    logger.warning("Broadcast failed to agent %s", aid)
        return count

    def is_connected(self, agent_id: str) -> bool:
        return agent_id in self.active_connections

    def get_online_agents(self) -> list[str]:
        return list(self.active_connections.keys())


# Module-level singleton
manager = ConnectionManager()
