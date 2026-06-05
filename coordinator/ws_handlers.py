"""WebSocket message handlers for the Agora Coordinator service.

PING, REGISTER, and SPEAK handlers. VOTE handler lives in ws_vote.py.
"""

from __future__ import annotations

import logging

from .models import MessageType
from .state import StateMachine
from .storage import Storage
from .ws import ConnectionManager

logger = logging.getLogger(__name__)


async def handle_ping(
    agent_id: str, payload: dict, mgr: ConnectionManager
) -> None:
    """Respond to PING with PONG."""
    await mgr.send(agent_id, {"type": MessageType.PONG})


async def handle_register(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process REGISTER: store agent info and mark online."""
    name = payload.get("name", agent_id)
    model = payload.get("model", "unknown")
    endpoint = payload.get("hermes_endpoint", "")
    caps = payload.get("capabilities", [])
    role = payload.get("role", "participant")

    await storage.register_agent(
        agent_id, name, model, endpoint, caps, role
    )
    await storage.set_agent_online(agent_id, True)

    await mgr.send(agent_id, {
        "type": MessageType.WELCOME,
        "agent_id": agent_id,
        "payload": {"message": "Registration successful"},
    })
    logger.info("Agent %s registered via WebSocket", agent_id)


async def handle_speak(
    agent_id: str, payload: dict, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Process SPEAK: validate, store, and broadcast."""
    motion_id = payload.get("motion_id")
    if not motion_id:
        await _send_error(mgr, agent_id, "missing_motion_id", "motion_id required")
        return

    if not await sm.can_speak(motion_id, agent_id):
        await _send_error(mgr, agent_id, "cannot_speak", "Not allowed to speak")
        return

    round_num = payload.get("round", 1)
    stance = payload.get("stance", "neutral")
    content = payload.get("content", "")
    evidence = payload.get("evidence", [])

    await storage.add_message(
        motion_id, agent_id, round_num, stance, content, evidence
    )

    broadcast_msg = {
        "type": MessageType.BROADCAST,
        "motion_id": motion_id,
        "agent_id": agent_id,
        "payload": {
            "round": round_num, "stance": stance,
            "content": content, "evidence": evidence,
        },
    }
    await mgr.broadcast(broadcast_msg, exclude=[agent_id])
    await mgr.send(agent_id, {
        "type": MessageType.BROADCAST,
        "motion_id": motion_id,
        "payload": {"delivered": True},
    })


async def _send_error(
    mgr: ConnectionManager, agent_id: str, code: str, message: str
) -> None:
    """Send an ERROR message to a specific agent."""
    await mgr.send(agent_id, {
        "type": MessageType.ERROR,
        "payload": {"code": code, "message": message},
    })
