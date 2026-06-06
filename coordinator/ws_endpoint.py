"""WebSocket endpoint for the Agora Coordinator service.

Provides the FastAPI WebSocket endpoint and message routing.
Phase 2: routes DEVILS_ADVOCATE_RESPONSE messages.
"""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

from .models import MessageType
from .ws import manager
from .ws_handlers import handle_ping, handle_register, handle_speak
from .ws_vote import handle_vote

logger = logging.getLogger(__name__)


async def websocket_endpoint(websocket: WebSocket, agent_id: str) -> None:
    """FastAPI WebSocket endpoint at /ws/{agent_id}."""
    if not await manager.connect(agent_id, websocket):
        return
    try:
        await manager.send(agent_id, {
            "type": MessageType.WELCOME,
            "agent_id": agent_id,
        })
        while True:
            data = await websocket.receive_text()
            await _route_message(agent_id, data)
    except Exception:
        pass
    finally:
        manager.disconnect(agent_id)
        await on_agent_disconnect(agent_id)


async def _route_message(agent_id: str, raw: str) -> None:
    """Parse and route a WebSocket message to the appropriate handler."""
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
        logger.error("WS deps not initialized")
        return

    if msg_type == MessageType.PING:
        await handle_ping(agent_id, payload, manager)
    elif msg_type == MessageType.REGISTER:
        await handle_register(agent_id, payload, storage, manager)
    elif msg_type == MessageType.SPEAK:
        await handle_speak(agent_id, payload, storage, sm, manager)
    elif msg_type == MessageType.VOTE:
        await handle_vote(agent_id, payload, storage, sm, manager)
    elif msg_type == MessageType.DEVILS_ADVOCATE_RESPONSE:
        await _handle_devils_advocate_response(
            agent_id, payload, storage, sm, manager)
    else:
        logger.warning("Unknown type from %s: %s", agent_id, msg_type)


async def _handle_devils_advocate_response(
    agent_id: str, payload: dict, storage, sm, mgr,
) -> None:
    """Process devil's advocate response: store as a SPEAK message."""
    motion_id = payload.get("motion_id")
    if not motion_id:
        return

    content = payload.get("content", "")
    round_num = payload.get("round", 1)

    await storage.add_message(
        motion_id, agent_id, round_num, "oppose", content,
        [{"source": "devils_advocate"}],
    )

    await mgr.broadcast({
        "type": MessageType.BROADCAST,
        "motion_id": motion_id,
        "agent_id": agent_id,
        "payload": {
            "round": round_num,
            "stance": "oppose",
            "content": content,
            "devils_advocate": True,
        },
    })


async def on_agent_disconnect(agent_id: str) -> None:
    """Mark agent offline and notify others."""
    if manager._storage is not None:
        await manager._storage.set_agent_online(agent_id, False)
    await manager.broadcast({
        "type": MessageType.AGENT_OFFLINE,
        "agent_id": agent_id,
    })
    logger.info("Agent %s went offline", agent_id)
