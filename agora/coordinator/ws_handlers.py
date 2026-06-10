"""WebSocket message handlers for the Agora Coordinator service.

PING, REGISTER, and SPEAK handlers. VOTE handler lives in ws_vote.py.
Smart discussion assessment lives in ws_smart.py.
Phase 9.3: Updated handle_register with new fields + AgentConfig.
"""

from __future__ import annotations

import logging
import secrets

from .deadlock_prevention import DeadlockDetector
from .models import MessageType
from .state import StateMachine
from .storage import Storage
from .ws import ConnectionManager
from .ws_smart import maybe_assess_round
from .token_rate_limiter import TokenRateLimiter

logger = logging.getLogger(__name__)

_deadlock_detector = DeadlockDetector()


async def handle_ping(
    agent_id: str, payload: dict, mgr: ConnectionManager
) -> None:
    """Respond to PING with PONG."""
    await mgr.send(agent_id, {"type": MessageType.PONG})


async def handle_register(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process REGISTER: store agent info and mark online.

    Phase 9.3: Uses new fields (agent_type, max_concurrent_tasks),
    generates agent_token, auto-approves WS-registered agents,
    and sends WELCOME with AgentConfig payload.
    """
    name = payload.get("name", agent_id)
    model = payload.get("model", "unknown")
    caps = payload.get("capabilities", [])
    role = payload.get("role", "participant")
    agent_type = payload.get("agent_type", "hermes")
    max_concurrent = payload.get("max_concurrent_tasks", 2)

    # Generate token on-the-fly for WS-based registration
    agent_token = f"ag-{secrets.token_hex(16)}"

    await storage.register_agent(
        agent_id, name, model,
        capabilities=caps, role=role,
        agent_type=agent_type,
        max_concurrent_tasks=max_concurrent,
        agent_token=agent_token,
        is_approved=True,
        approval_status="approved",
    )
    await storage.set_agent_online(agent_id, True)

    # Read persisted config (includes tpm_limit/tpm_burst_factor)
    agent = await storage.get_agent(agent_id)
    tpm_limit = agent.get("tpm_limit", 10000) if agent else 10000
    tpm_burst = agent.get("tpm_burst_factor", 1.5) if agent else 1.5

    await mgr.send(agent_id, {
        "type": MessageType.WELCOME,
        "agent_id": agent_id,
        "payload": {
            "message": "Registration successful",
            "agent_token": agent_token,
            "config": {
                "heartbeat_interval_seconds": 30,
                "heartbeat_timeout_seconds": 120,
                "tpm_limit": tpm_limit,
                "tpm_burst_factor": tpm_burst,
                "max_concurrent_tasks": max_concurrent,
            },
        },
    })
    logger.info("Agent %s registered via WebSocket", agent_id)


async def handle_heartbeat(
    agent_id: str, payload: dict, storage: Storage,
    mgr: ConnectionManager,
) -> None:
    """Process HEARTBEAT: update load, active_tasks, capabilities, last_seen.

    Fire-and-forget: no response sent back to the agent.
    Coordinator uses this data for assignment and offline detection.
    """
    load = float(payload.get("load", 0.0))
    active_tasks = payload.get("active_tasks", [])
    await storage.update_agent_heartbeat(
        agent_id, load=load, active_tasks=active_tasks,
    )
    caps = payload.get("capabilities")
    if caps is not None:
        await storage.update_agent_capabilities(agent_id, caps)
    model = payload.get("model")
    if model is not None:
        await storage.update_agent_model(agent_id, model)


async def handle_speak(
    agent_id: str, payload: dict, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Process SPEAK: validate, store, broadcast, and assess round."""
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

    # Deadlock detection
    _deadlock_detector.track_reference(agent_id, motion_id, str(round_num))
    for risk_a, risk_b, status in _deadlock_detector.get_deadlock_risk():
        if status.value == "deadlock":
            break_msg = _deadlock_detector.inject_break_signal(risk_a, risk_b)
            await mgr.broadcast(break_msg)


async def _send_error(
    mgr: ConnectionManager, agent_id: str, code: str, message: str
) -> None:
    """Send an ERROR message to a specific agent."""
    await mgr.send(agent_id, {
        "type": MessageType.ERROR,
        "payload": {"code": code, "message": message},
    })
