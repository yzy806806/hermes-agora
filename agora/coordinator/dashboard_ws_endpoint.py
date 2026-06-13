"""Dashboard WebSocket endpoint function.

Phase 13.2a: /ws/dashboard route handler.
Validates JWT from query param, handles subscribe/unsubscribe
including project-level subscriptions.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import WebSocket

from .dashboard_ws import CHANNEL_EVENTS, CHANNEL_NOTIFICATIONS, dashboard_hub

logger = logging.getLogger(__name__)


async def dashboard_ws_endpoint(
    websocket: WebSocket, token: str = "",
) -> None:
    """FastAPI WebSocket endpoint at /ws/dashboard?token=<jwt>.

    Connection flow:
    1. Client connects with JWT in query param
    2. Server validates JWT, upgrades to WS
    3. Server sends WELCOME with role + tenant_id
    4. Client sends SUBSCRIBE/UNSUBSCRIBE for channel filtering
    5. Client sends SUBSCRIBE_PROJECT/UNSUBSCRIBE_PROJECT for
       per-project event filtering
    6. Server pushes subscribed events
    """
    client_id = f"dashboard:{uuid.uuid4().hex[:8]}"
    success, role, tenant_id = await dashboard_hub.connect(
        client_id, websocket, token,
    )
    if not success:
        return
    try:
        # Send WELCOME
        client = dashboard_hub._clients[client_id]
        await client.send({
            "type": "WELCOME",
            "payload": {"role": role, "tenant_id": tenant_id},
        })
        # Auto-subscribe to default channels
        client.subscriptions.add(CHANNEL_EVENTS)
        client.subscriptions.add(CHANNEL_NOTIFICATIONS)
        while True:
            data = await websocket.receive_text()
            await dashboard_hub.handle_message(client_id, data)
    except Exception:
        pass
    finally:
        dashboard_hub.disconnect(client_id)
