"""Dashboard WebSocket endpoint function.

Phase 11.2b: /ws/dashboard route handler.
Validates JWT from query param, handles subscribe/unsubscribe.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import WebSocket

from .dashboard_ws import dashboard_hub

logger = logging.getLogger(__name__)


async def dashboard_ws_endpoint(
    websocket: WebSocket, token: str = "",
) -> None:
    """FastAPI WebSocket endpoint at /ws/dashboard?token=<jwt>.

    Connection flow:
    1. Client connects with JWT in query param
    2. Server validates JWT, upgrades to WS
    3. Server sends WELCOME with role + tenant_id
    4. Client sends SUBSCRIBE/UNSUBSCRIBE for event filtering
    5. Server pushes subscribed events
    """
    client_id = f"dashboard:{uuid.uuid4().hex[:8]}"
    success, role, tenant_id = await dashboard_hub.connect(
        client_id, websocket, token,
    )
    if not success:
        return
    try:
        # Send WELCOME
        await dashboard_hub._clients[client_id].send({
            "type": "WELCOME",
            "payload": {"role": role, "tenant_id": tenant_id},
        })
        # Auto-subscribe to 'events' channel
        dashboard_hub._clients[client_id].subscriptions.add("events")
        while True:
            data = await websocket.receive_text()
            await dashboard_hub.handle_message(client_id, data)
    except Exception:
        pass
    finally:
        dashboard_hub.disconnect(client_id)
