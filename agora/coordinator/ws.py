"""WebSocket connection manager for the Agora Coordinator service.

Phase 8.2: Per-tenant ConnectionHub isolation.
Each tenant has its own ConnectionHub, so agents only see messages
from agents in the same tenant.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from .state import StateMachine
    from .storage import Storage

logger = logging.getLogger(__name__)


class ConnectionHub:
    """Manages WebSocket connections for a single tenant."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self._storage: Optional[Storage] = None
        self._state_machine: Optional[StateMachine] = None
        self._app_state: Any = None

    def set_deps(self, storage: Storage, sm: StateMachine) -> None:
        self._storage = storage
        self._state_machine = sm

    def set_app_state(self, app_state: Any) -> None:
        """Store FastAPI app.state for accessing shared components."""
        self._app_state = app_state

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
        self.active_connections.pop(agent_id, None)
        logger.info("Agent %s disconnected from WebSocket", agent_id)

    async def send(self, agent_id: str, message: dict[str, Any]) -> bool:
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


class ConnectionManager:
    """Multi-tenant WebSocket connection manager.

    Manages per-tenant ConnectionHub instances.
    """

    def __init__(self) -> None:
        self._hubs: dict[str, ConnectionHub] = {}
        self._default_hub = ConnectionHub()

    def get_hub(self, tenant_id: str) -> ConnectionHub:
        """Get or create a ConnectionHub for a tenant."""
        if tenant_id == "default":
            return self._default_hub
        if tenant_id not in self._hubs:
            self._hubs[tenant_id] = ConnectionHub()
        return self._hubs[tenant_id]

    def set_deps(self, storage: Storage, sm: StateMachine) -> None:
        """Set deps on the default hub (backward compat)."""
        self._default_hub.set_deps(storage, sm)

    def set_tenant_deps(self, tenant_id: str, storage: Storage,
                        sm: StateMachine) -> None:
        """Set deps on a specific tenant's hub."""
        hub = self.get_hub(tenant_id)
        hub.set_deps(storage, sm)

    def set_app_state(self, app_state: Any) -> None:
        """Set app.state on all hubs for shared component access."""
        self._default_hub.set_app_state(app_state)
        for hub in self._hubs.values():
            hub.set_app_state(app_state)

    # Backward-compat proxies to default hub
    @property
    def active_connections(self) -> dict[str, WebSocket]:
        return self._default_hub.active_connections

    @property
    def _storage(self) -> Optional[Storage]:
        return self._default_hub._storage

    @property
    def _state_machine(self) -> Optional[StateMachine]:
        return self._default_hub._state_machine

    @property
    def _app_state(self) -> Any:
        return self._default_hub._app_state

    async def connect(self, agent_id: str, websocket: WebSocket) -> bool:
        return await self._default_hub.connect(agent_id, websocket)

    def disconnect(self, agent_id: str) -> None:
        self._default_hub.disconnect(agent_id)

    async def send(self, agent_id: str, message: dict[str, Any]) -> bool:
        return await self._default_hub.send(agent_id, message)

    async def broadcast(
        self, message: dict[str, Any], exclude: list[str] | None = None
    ) -> int:
        return await self._default_hub.broadcast(message, exclude)

    def is_connected(self, agent_id: str) -> bool:
        return self._default_hub.is_connected(agent_id)

    def get_online_agents(self) -> list[str]:
        return self._default_hub.get_online_agents()


# Module-level singleton
manager = ConnectionManager()
