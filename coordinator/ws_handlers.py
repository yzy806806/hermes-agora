"""WebSocket message handlers for the Agora Coordinator service.

PING, REGISTER, and SPEAK handlers. VOTE handler lives in ws_vote.py.
Smart discussion assessment lives in ws_smart.py.
"""

from __future__ import annotations

import logging

from .deadlock_prevention import DeadlockDetector
from .models import MessageType
from .state import StateMachine
from .storage import Storage
from .ws import ConnectionManager
from .ws_smart import maybe_assess_round

logger = logging.getLogger(__name__)

_deadlock_detector = DeadlockDetector()


async def handle_ping(
    agent_id: str, payload: dict, mgr: ConnectionManager
) -> None:
    """Respond to PING with PONG.

    Args:
        agent_id: ID of the pinging agent.
        payload: Ping payload (usually empty).
        mgr: ConnectionManager for sending responses.
    """
    await mgr.send(agent_id, {"type": MessageType.PONG})


async def handle_register(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process REGISTER: store agent info and mark online.

    Extracts name, model, endpoint, capabilities, and role from
    the payload, persists them via Storage, and confirms registration.

    Args:
        agent_id: ID of the registering agent.
        payload: Registration data (name, model, hermes_endpoint, etc).
        storage: Storage instance for persisting agent data.
        mgr: ConnectionManager for sending confirmation.
    """
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
    """Process SPEAK: validate, store, broadcast, and assess round.

    Validates the agent can speak, stores the message, broadcasts
    to other participants, and triggers round assessment.

    Args:
        agent_id: ID of the speaking agent.
        payload: Speak payload (motion_id, round, stance, content).
        storage: Storage instance for persisting messages.
        sm: StateMachine for checking speak permissions.
        mgr: ConnectionManager for broadcasting.
    """
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

    # Phase 2: check if round complete and assess
    await maybe_assess_round(motion_id, storage, sm, mgr)

    # Deadlock detection: track references and check for cycles
    _deadlock_detector.track_reference(agent_id, motion_id, str(round_num))
    for risk_a, risk_b, status in _deadlock_detector.get_deadlock_risk():
        if status.value == "deadlock":
            break_msg = _deadlock_detector.inject_break_signal(risk_a, risk_b)
            await mgr.broadcast(break_msg)


async def _send_error(
    mgr: ConnectionManager, agent_id: str, code: str, message: str
) -> None:
    """Send an ERROR message to a specific agent.

    Args:
        mgr: ConnectionManager for sending the error.
        agent_id: Target agent ID.
        code: Error code string.
        message: Human-readable error description.
    """
    await mgr.send(agent_id, {
        "type": MessageType.ERROR,
        "payload": {"code": code, "message": message},
    })
