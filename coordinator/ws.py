"""WebSocket connection manager, endpoint, and message routing."""

from __future__ import annotations

import json
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
        self._storage = storage
        self._state_machine = sm

    async def connect(self, agent_id: str, websocket: WebSocket) -> bool:
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
        logger.info("Agent %s connected", agent_id)
        return True

    def disconnect(self, agent_id: str) -> None:
        self.active_connections.pop(agent_id, None)

    async def send(self, agent_id: str, message: dict) -> bool:
        ws = self.active_connections.get(agent_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            return False

    async def broadcast(self, message: dict, exclude: list[str] | None = None) -> int:
        exclude_set = set(exclude or [])
        count = 0
        for aid, ws in list(self.active_connections.items()):
            if aid not in exclude_set:
                try:
                    await ws.send_json(message)
                    count += 1
                except Exception:
                    pass
        return count

    def get_online_agents(self) -> list[str]:
        return list(self.active_connections.keys())


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, agent_id: str) -> None:
    """FastAPI WebSocket endpoint."""
    if not await manager.connect(agent_id, websocket):
        return
    try:
        await manager.send(agent_id, {"type": "WELCOME", "agent_id": agent_id})
        while True:
            data = await websocket.receive_text()
            await _route_message(agent_id, data)
    except Exception:
        pass
    finally:
        manager.disconnect(agent_id)
        await on_agent_disconnect(agent_id)


async def _route_message(agent_id: str, raw: str) -> None:
    """Parse and route a WebSocket message."""
    from .models import MessageType
    from .ws_handlers import handle_ping, handle_register, handle_speak, handle_vote

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await manager.send(agent_id, {
            "type": MessageType.ERROR,
            "payload": {"code": "invalid_json", "message": "Bad JSON"},
        })
        return
    msg_type = msg.get("type", "")
    payload = msg.get("payload", {})
    storage = manager._storage
    sm = manager._state_machine
    if storage is None or sm is None:
        return
    if msg_type == MessageType.PING:
        await handle_ping(agent_id, payload, manager)
    elif msg_type == MessageType.REGISTER:
        await handle_register(agent_id, payload, storage, manager)
    elif msg_type == MessageType.SPEAK:
        await handle_speak(agent_id, payload, storage, sm, manager)
    elif msg_type == MessageType.VOTE:
        await handle_vote(agent_id, payload, storage, sm, manager)


async def on_agent_disconnect(agent_id: str) -> None:
    """Mark agent offline and notify others."""
    from .models import MessageType
    if manager._storage is not None:
        await manager._storage.set_agent_online(agent_id, False)
    await manager.broadcast({"type": MessageType.AGENT_OFFLINE, "agent_id": agent_id})
