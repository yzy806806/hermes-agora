"""Smart discussion flow logic for the Agora Coordinator.

Handles round-complete detection, assessment triggering, and
smart state transitions (consensus, devil's advocate, redirect).
"""

from __future__ import annotations

import logging

from .assessment import AssessmentResult, QualityAssessor
from .devils_advocate import DevilsAdvocateManager
from .models import MessageType, MotionStatus
from .state import InvalidTransitionError, StateMachine
from .storage import Storage
from .ws import ConnectionManager

logger = logging.getLogger(__name__)

_assessor = QualityAssessor()


async def maybe_assess_round(
    motion_id: str,
    storage: Storage,
    sm: StateMachine,
    mgr: ConnectionManager,
) -> None:
    """Check if round is complete; if so, run assessment and act.

    Verifies all agents have spoken in the current round, runs
    quality assessment, saves results, broadcasts to participants,
    and triggers appropriate follow-up actions.

    Args:
        motion_id: ID of the motion to assess.
        storage: Storage instance for querying messages.
        sm: StateMachine for state transitions.
        mgr: ConnectionManager for broadcasting.
    """
    motion = await storage.get_motion(motion_id)
    if motion is None:
        return

    # Only assess for motions in discussing state with smart_mode
    if motion["status"] != MotionStatus.DISCUSSING:
        return

    current_round = motion["current_round"]
    if current_round == 0:
        return

    # Check if all agents have spoken this round
    agents = await storage.list_agents()
    if not agents:
        return

    round_msgs = await storage.get_messages(motion_id, round_num=current_round)
    spoken = {m.get("agent_id") for m in round_msgs}
    all_agent_ids = {a["agent_id"] for a in agents}

    if not all_agent_ids.issubset(spoken):
        return  # Round not complete yet

    # Round complete — run assessment
    assessment = await _assessor.assess(motion_id, storage)

    # Save assessment to DB
    await storage.save_assessment(
        motion_id=motion_id,
        round_num=current_round,
        result=assessment.result.value,
        consensus_level=assessment.consensus_level.value,
        metrics={
            "total_messages": assessment.metrics.total_messages,
            "argument_quality_score": assessment.metrics.argument_quality_score,
            "topic_relevance_score": assessment.metrics.topic_relevance_score,
        },
        rationale=assessment.rationale,
    )

    # Broadcast assessment
    await mgr.broadcast({
        "type": MessageType.ASSESSMENT,
        "motion_id": motion_id,
        "payload": {
            "result": assessment.result.value,
            "consensus_level": assessment.consensus_level.value,
            "metrics": {
                "total_messages": assessment.metrics.total_messages,
                "argument_quality": assessment.metrics.argument_quality_score,
                "topic_relevance": assessment.metrics.topic_relevance_score,
            },
            "rationale": assessment.rationale,
            "recommendations": assessment.recommendations,
        },
    })

    # Act on assessment result
    await _act_on_assessment(
        motion_id, assessment, storage, sm, mgr)


async def _act_on_assessment(
    motion_id: str, assessment, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Take action based on assessment result.

    Routes to voting on consensus/sufficient, sends topic redirect
    on off-topic, triggers devil advocate, or continues discussion.

    Args:
        motion_id: ID of the motion.
        assessment: AssessmentResult object with result and metrics.
        storage: Storage instance for data queries.
        sm: StateMachine for state transitions.
        mgr: ConnectionManager for broadcasting.
    """
    result = assessment.result

    if result in (AssessmentResult.CONSENSUS_REACHED,
                  AssessmentResult.SUFFICIENT):
        await _transition_to_voting(motion_id, sm, mgr)

    elif result == AssessmentResult.OFF_TOPIC:
        await mgr.broadcast({
            "type": MessageType.TOPIC_REDIRECT,
            "motion_id": motion_id,
            "payload": {
                "message": "讨论偏离主题，请聚焦于：",
                "focus_areas": assessment.metrics.key_points_identified[:3],
                "unresolved": assessment.metrics.unresolved_points[:3],
            },
        })
        await _continue_next_round(motion_id, storage, sm, mgr)

    elif result == AssessmentResult.DEVILS_ADVOCATE:
        da_mgr = DevilsAdvocateManager(storage, mgr)
        should, target = await da_mgr.should_trigger(motion_id)
        if should and target:
            await da_mgr.trigger(motion_id, target)
        await _continue_next_round(motion_id, storage, sm, mgr)

    else:  # NEEDS_MORE
        await _continue_next_round(motion_id, storage, sm, mgr)


async def _transition_to_voting(
    motion_id: str, sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Move motion to voting phase.

    Transitions the motion state and broadcasts a vote request.

    Args:
        motion_id: ID of the motion to transition.
        sm: StateMachine for state transitions.
        mgr: ConnectionManager for broadcasting.
    """
    try:
        await sm.transition(motion_id, "start_voting")
        await mgr.broadcast({
            "type": MessageType.REQUEST_VOTE,
            "motion_id": motion_id,
            "payload": {"reason": "assessment_triggered"},
        })
    except (InvalidTransitionError, ValueError) as exc:
        logger.warning("Assessment->voting transition failed: %s", exc)


async def _continue_next_round(
    motion_id: str, storage: Storage,
    sm: StateMachine, mgr: ConnectionManager,
) -> None:
    """Continue to next discussion round.

    Increments the round counter if below max rounds, otherwise
    transitions to voting. Broadcasts round completion.

    Args:
        motion_id: ID of the motion.
        storage: Storage instance for round increment.
        sm: StateMachine for state transitions.
        mgr: ConnectionManager for broadcasting.
    """
    motion = await storage.get_motion(motion_id)
    if motion is None:
        return

    current = motion["current_round"]
    max_rounds = motion["rounds"]

    if current >= max_rounds:
        await _transition_to_voting(motion_id, sm, mgr)
        return

    try:
        await sm.transition(motion_id, "round_complete")
    except (InvalidTransitionError, ValueError) as exc:
        logger.warning("Round transition failed: %s", exc)
        return

    new_round = await storage.increment_round(motion_id)
    await mgr.broadcast({
        "type": MessageType.ROUND_COMPLETE,
        "motion_id": motion_id,
        "payload": {"round": current, "next_round": new_round},
    })
