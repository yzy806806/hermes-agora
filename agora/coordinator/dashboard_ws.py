"""Dashboard WebSocket endpoint with JWT authentication.

Phase 11.2b: Real-time event feed for the web dashboard.
Separate from agent WS (/ws/{agent_id}) because:
- Dashboard is a human viewer, not an agent
- Different message types (read-only observation)
- Different auth (JWT login vs agent token)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

from .models import MessageType
from .token_manager import TokenManager

logger = logging.getLogger(__name__)

# Event types pushed to dashboard
DASHBOARD_EVENTS = [
    "DISCUSSION_UPDATE",
    "TASK_UPDATE",
    "AGENT_STATUS",
    "PLUGIN_EVENT",
    "AUDIT_EVENT",
]


class DashboardClient:
    """Represents a connected dashboard client."""

    def __init__(self, websocket: WebSocket, role: str, tenant_id: str | None):
        self.websocket = websocket
        self.role = role
        self.tenant_id = tenant_id
        self.subscriptions: set[str] = set()

    async def send(self, message: dict[str, Any]) -> bool:
        try:
            await self.websocket.send_json(message)
            return True
        except Exception:
            return False


class DashboardHub:
    """Manages connected dashboard clients."""

    def __init__(self) -> None:
        self._clients: dict[str, DashboardClient] = {}
        self._token_mgr: TokenManager | None = None

    def set_token_manager(self, token_mgr: TokenManager) -> None:
        self._token_mgr = token_mgr

    async def connect(
        self, client_id: str, websocket: WebSocket, token: str,
    ) -> tuple[bool, str, str | None]:
        """Validate JWT and accept connection.

        Returns (success, role, tenant_id).
        """
        if self._token_mgr is None:
            await websocket.close(code=1011, reason="Server not initialized")
            return False, "", None
        try:
            payload = self._token_mgr.validate_token(token)
        except ValueError as e:
            await websocket.close(code=4003, reason=f"Invalid token: {e}")
            return False, "", None
        await websocket.accept()
        client = DashboardClient(
            websocket, payload.role, payload.tenant_id,
        )
        self._clients[client_id] = client
        logger.info("Dashboard client %s connected (role=%s)", client_id, payload.role)
        return True, payload.role, payload.tenant_id

    def disconnect(self, client_id: str) -> None:
        self._clients.pop(client_id, None)
        logger.info("Dashboard client %s disconnected", client_id)

    async def handle_message(self, client_id: str, raw: str) -> None:
        """Route message from dashboard client."""
        client = self._clients.get(client_id)
        if client is None:
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await client.send({
                "type": MessageType.ERROR,
                "payload": {"code": "invalid_json", "message": "Bad JSON"},
            })
            return
        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        if msg_type == "SUBSCRIBE":
            channels = payload.get("channels", [])
            client.subscriptions.update(channels)
            await client.send({
                "type": "SUBSCRIBED",
                "payload": {"channels": list(client.subscriptions)},
            })
        elif msg_type == "UNSUBSCRIBE":
            channels = payload.get("channels", [])
            client.subscriptions.difference_update(channels)
            await client.send({
                "type": "UNSUBSCRIBED",
                "payload": {"channels": list(client.subscriptions)},
            })
        else:
            logger.warning("Unknown dashboard message type: %s", msg_type)

    async def broadcast_event(
        self, event_type: str, payload: dict[str, Any],
        channel: str = "events",
    ) -> int:
        """Broadcast an event to subscribed dashboard clients."""
        count = 0
        for client in self._clients.values():
            if channel in client.subscriptions:
                sent = await client.send({
                    "type": event_type,
                    "payload": payload,
                })
                if sent:
                    count += 1
        return count


# Module-level singleton
dashboard_hub = DashboardHub()
