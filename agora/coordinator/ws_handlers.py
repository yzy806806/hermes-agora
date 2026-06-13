"""WebSocket message handlers for the Agora Coordinator service.

PING, REGISTER, and SPEAK handlers. VOTE handler lives in ws_vote.py.
Smart discussion assessment lives in ws_smart.py.
Phase 9.3: Updated handle_register with new fields + AgentConfig.
Phase 13.1f: Added PIPELINE_* message handlers for dashboard push.
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
    logger.info("Agent %s registered via WebSocket")

    # Phase 11.5a: Push to dashboard event bus
    from .event_bus import publish
    await publish("AGENT_ONLINE", {
        "agent_id": agent_id, "name": name, "model": model,
    }, channel="events")


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
        "type": MessageType.SPEECH_ADDED,
        "motion_id": motion_id,
        "agent_id": agent_id,
        "payload": {
            "round": round_num, "stance": stance,
            "content": content, "evidence": evidence,
        },
    }
    await mgr.broadcast(broadcast_msg, exclude=[agent_id])
    await mgr.send(agent_id, {
        "type": MessageType.SPEECH_ADDED,
        "motion_id": motion_id,
        "payload": {"delivered": True},
    })

    # Phase 11.5a: Push to dashboard event bus
    from .event_bus import publish
    await publish("DISCUSSION_MESSAGE", {
        "motion_id": motion_id, "agent_id": agent_id,
        "round": round_num, "stance": stance,
        "content": content,
    }, channel="discussions")

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


# ---------------------------------------------------------------------------
# Phase 13.1f: Pipeline WS message handlers
# ---------------------------------------------------------------------------

async def handle_pipeline_phase_change(
    pipeline_id: str, phase: str, project_id: str,
    prev_phase: str | None = None,
) -> int:
    """Broadcast PIPELINE_PHASE_CHANGE to dashboard clients."""
    from .event_bus import publish
    return await publish("PIPELINE_PHASE_CHANGE", {
        "pipeline_id": pipeline_id,
        "phase": phase,
        "previous_phase": prev_phase,
        "project_id": project_id,
    }, channel="pipelines")


async def handle_pipeline_task_update(
    pipeline_id: str, task_id: str, status: str,
    project_id: str, agent_id: str | None = None,
) -> int:
    """Broadcast PIPELINE_TASK_UPDATE to dashboard clients."""
    from .event_bus import publish
    return await publish("PIPELINE_TASK_UPDATE", {
        "pipeline_id": pipeline_id,
        "task_id": task_id,
        "status": status,
        "agent_id": agent_id,
        "project_id": project_id,
    }, channel="pipelines")


async def handle_pipeline_completed(
    pipeline_id: str, project_id: str,
    tasks_total: int = 0, tasks_completed: int = 0,
    tasks_failed: int = 0, release_version: str | None = None,
) -> int:
    """Broadcast PIPELINE_COMPLETED to dashboard clients."""
    from .event_bus import publish
    return await publish("PIPELINE_COMPLETED", {
        "pipeline_id": pipeline_id,
        "project_id": project_id,
        "tasks_total": tasks_total,
        "tasks_completed": tasks_completed,
        "tasks_failed": tasks_failed,
        "release_version": release_version,
    }, channel="pipelines")


async def handle_pipeline_error(
    pipeline_id: str, project_id: str,
    error: str, phase: str | None = None,
) -> int:
    """Broadcast PIPELINE_ERROR to dashboard clients."""
    from .event_bus import publish
    return await publish("PIPELINE_ERROR", {
        "pipeline_id": pipeline_id,
        "project_id": project_id,
        "error": error,
        "phase": phase,
    }, channel="pipelines")
