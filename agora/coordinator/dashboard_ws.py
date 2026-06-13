"""Dashboard WebSocket hub — event fan-out with subscription filtering.

Phase 13.2a: Upgraded from Phase 11.2b.
- Clients subscribe to channels (events, notifications, pipelines)
- Clients subscribe to project_ids for per-project filtering
- broadcast_event filters by channel AND project_id
- Tracks connected clients; auto-cleans stale connections
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

from .models import MessageType

logger = logging.getLogger(__name__)

# Channels available for subscription
CHANNEL_EVENTS = "events"
CHANNEL_NOTIFICATIONS = "notifications"
CHANNEL_PIPELINES = "pipelines"
ALL_CHANNELS = {CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS, CHANNEL_PIPELINES}


class DashboardClient:
    """Represents a connected dashboard client."""

    def __init__(self, websocket: WebSocket, role: str, tenant_id: str | None):
        self.websocket = websocket
        self.role = role
        self.tenant_id = tenant_id
        self.subscriptions: set[str] = set()
        self.project_subscriptions: set[str] = set()

    async def send(self, message: dict[str, Any]) -> bool:
        try:
            await self.websocket.send_json(message)
            return True
        except Exception:
            return False


class DashboardHub:
    """Manages connected dashboard clients with fan-out."""

    def __init__(self) -> None:
        self._clients: dict[str, DashboardClient] = {}
        self._token_mgr: Any = None

    def set_token_manager(self, token_mgr: Any) -> None:
        self._token_mgr = token_mgr

    @property
    def connected_clients(self) -> int:
        return len(self._clients)

    async def connect(
        self, client_id: str, websocket: WebSocket, token: str,
    ) -> tuple[bool, str, str | None]:
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
            self._handle_subscribe(client, payload)
        elif msg_type == "UNSUBSCRIBE":
            self._handle_unsubscribe(client, payload)
        elif msg_type == "SUBSCRIBE_PROJECT":
            self._handle_project_subscribe(client, payload)
        elif msg_type == "UNSUBSCRIBE_PROJECT":
            self._handle_project_unsubscribe(client, payload)
        else:
            logger.warning("Unknown dashboard message type: %s", msg_type)

    def _handle_subscribe(self, client: DashboardClient, payload: dict) -> None:
        channels = set(payload.get("channels", [])) & ALL_CHANNELS
        client.subscriptions.update(channels)

    def _handle_unsubscribe(self, client: DashboardClient, payload: dict) -> None:
        channels = set(payload.get("channels", []))
        client.subscriptions.difference_update(channels)

    def _handle_project_subscribe(
        self, client: DashboardClient, payload: dict,
    ) -> None:
        pids = set(payload.get("project_ids", []))
        client.project_subscriptions.update(pids)

    def _handle_project_unsubscribe(
        self, client: DashboardClient, payload: dict,
    ) -> None:
        pids = set(payload.get("project_ids", []))
        client.project_subscriptions.difference_update(pids)

    async def broadcast_event(
        self, event_type: str, payload: dict[str, Any],
        channel: str = CHANNEL_EVENTS,
    ) -> int:
        """Broadcast event to clients subscribed to channel + project."""
        project_id = payload.get("project_id")
        count = 0
        stale: list[str] = []
        for cid, client in self._clients.items():
            if channel not in client.subscriptions:
                continue
            if project_id and client.project_subscriptions:
                if project_id not in client.project_subscriptions:
                    continue
            sent = await client.send({"type": event_type, "payload": payload})
            if sent:
                count += 1
            else:
                stale.append(cid)
        for cid in stale:
            self._clients.pop(cid, None)
            logger.info("Cleaned up stale dashboard client %s", cid)
        return count


# Module-level singleton
dashboard_hub = DashboardHub()
