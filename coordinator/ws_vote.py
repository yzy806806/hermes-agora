"""WebSocket VOTE handler for the Agora Coordinator service.

Handles vote casting, confirmation, and auto-completion detection.
"""

from __future__ import annotations

import logging

from .models import MessageType
from .state import StateMachine, InvalidTransitionError
from .storage import Storage
from .ws import ConnectionManager
from .ws_handlers import _send_error

logger = logging.getLogger(__name__)


async def handle_vote(
    agent_id: str, payload: dict, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Process VOTE: validate, store, confirm, and check completion."""
    motion_id = payload.get("motion_id")
    if not motion_id:
        await _send_error(mgr, agent_id, "missing_motion_id", "motion_id required")
        return

    if not await sm.can_vote(motion_id, agent_id):
        await _send_error(mgr, agent_id, "cannot_vote", "Not allowed to vote")
        return

    vote = payload.get("vote", "abstain")
    confidence = payload.get("confidence", 1.0)
    reason = payload.get("reason")

    await storage.add_vote(motion_id, agent_id, vote, confidence, reason)

    await mgr.send(agent_id, {
        "type": MessageType.VOTE_CONFIRMED,
        "motion_id": motion_id,
        "payload": {"vote": vote, "agent_id": agent_id},
    })

    # Check if all online agents have voted
    online_agents = await storage.list_agents(online_only=True)
    all_voted = True
    for ag in online_agents:
        if not await storage.has_voted(motion_id, ag["agent_id"]):
            all_voted = False
            break

    if all_voted and online_agents:
        try:
            await sm.transition(motion_id, "all_voted")
            summary = await storage.get_vote_summary(motion_id)
            await mgr.broadcast({
                "type": MessageType.RESULT,
                "motion_id": motion_id,
                "payload": summary,
            })
        except (InvalidTransitionError, ValueError) as exc:
            logger.warning("Vote completion transition failed: %s", exc)
