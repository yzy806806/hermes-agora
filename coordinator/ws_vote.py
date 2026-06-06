"""WebSocket VOTE handler for the Agora Coordinator service.

Handles vote casting, confirmation, and auto-completion detection.
Phase 2: supports binary, ranking, approval, and range vote formats.
"""

from __future__ import annotations

import json
import logging

from .models import MessageType, VotingMethod
from .state import StateMachine, InvalidTransitionError
from .storage import Storage
from .ws import ConnectionManager
from .ws_handlers import _send_error

logger = logging.getLogger(__name__)

# Map vote_type string to recognized types
_BINARY_METHODS = {
    VotingMethod.SIMPLE_MAJORITY, VotingMethod.SUPERMAJORITY,
    VotingMethod.UNANIMOUS, VotingMethod.WEIGHTED,
}


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

    motion = await storage.get_motion(motion_id)
    if motion is None:
        await _send_error(mgr, agent_id, "not_found", "Motion not found")
        return

    vote_type = payload.get("type", "binary")
    voting_method = motion.get("voting_method", "simple_majority")

    # Validate vote format matches the voting method
    if not _validate_vote_format(voting_method, vote_type, payload):
        await _send_error(
            mgr, agent_id, "invalid_vote_format",
            f"Vote format '{vote_type}' not valid for method '{voting_method}'")
        return

    # Extract vote value and data based on type
    vote_value, vote_data = _extract_vote_data(vote_type, payload)
    confidence = payload.get("confidence", 1.0)
    reason = payload.get("reason")

    vote_data_json = json.dumps(vote_data) if vote_data else None

    await storage.add_vote(
        motion_id, agent_id, vote_value, confidence, reason,
        vote_type=vote_type, vote_data=vote_data_json)

    await mgr.send(agent_id, {
        "type": MessageType.VOTE_CONFIRMED,
        "motion_id": motion_id,
        "payload": {"vote": vote_value, "agent_id": agent_id},
    })

    # Check if all online agents have voted
    await _check_all_voted(motion_id, storage, sm, mgr)


def _validate_vote_format(
    voting_method: str, vote_type: str, payload: dict,
) -> bool:
    """Check if vote format matches the voting method."""
    try:
        method = VotingMethod(voting_method)
    except ValueError:
        return True  # Unknown method, allow

    if method in _BINARY_METHODS:
        return vote_type == "binary" and "vote" in payload
    elif method == VotingMethod.RANKED_CHOICE:
        return vote_type == "ranking" and "ranking" in payload
    elif method == VotingMethod.APPROVAL:
        return vote_type == "approval" and "approved" in payload
    elif method == VotingMethod.RANGE:
        return vote_type == "range" and "scores" in payload
    elif method == VotingMethod.BORDA_COUNT:
        return vote_type == "ranking" and "ranking" in payload
    elif method == VotingMethod.INSTANT_RUNOFF:
        return vote_type == "ranking" and "ranking" in payload
    return True


def _extract_vote_data(
    vote_type: str, payload: dict,
) -> tuple[str, dict | None]:
    """Extract vote value and structured data from payload."""
    if vote_type == "binary":
        return payload.get("vote", "abstain"), None
    elif vote_type == "ranking":
        ranking = payload.get("ranking", [])
        return "ranking", {"ranking": ranking}
    elif vote_type == "approval":
        approved = payload.get("approved", [])
        return "approval", {"approved": approved}
    elif vote_type == "range":
        scores = payload.get("scores", {})
        return "range", {"scores": scores}
    elif vote_type == "multiple_choice":
        return payload.get("vote", ""), {"type": "multiple_choice"}
    return payload.get("vote", "abstain"), None


async def _check_all_voted(
    motion_id: str, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Check if all online agents have voted, then close."""
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
