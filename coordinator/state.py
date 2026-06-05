"""Discussion state machine for the Agora Coordinator service.

Manages motion lifecycle transitions and permission checks
(speak / vote) based on current state and agent registration.
"""

from __future__ import annotations

import logging
from typing import Optional

from .models import MotionStatus
from .storage import Storage

logger = logging.getLogger(__name__)

# Valid state transitions: (current_status, event) -> new_status
_TRANSITIONS: dict[tuple[str, str], MotionStatus] = {
    (MotionStatus.DRAFT, "start"): MotionStatus.DISCUSSING,
    (MotionStatus.DISCUSSING, "round_complete"): MotionStatus.DISCUSSING,
    (MotionStatus.DISCUSSING, "start_voting"): MotionStatus.VOTING,
    (MotionStatus.VOTING, "all_voted"): MotionStatus.CLOSED,
    (MotionStatus.VOTING, "force_close"): MotionStatus.CLOSED,
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""


class StateMachine:
    """Discussion state machine.

    Transition rules:
        draft -> discussing  (event: "start")
        discussing -> discussing  (event: "round_complete", if rounds remain)
        discussing -> voting  (event: "start_voting", when all rounds done)
        voting -> closed  (event: "all_voted" or "force_close")
    """

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    async def transition(
        self, motion_id: str, event: str
    ) -> MotionStatus:
        """Execute a state transition and return the new status.

        For the "round_complete" event on a DISCUSSING motion, the method
        checks whether all rounds are exhausted. If so, it auto-promotes
        to VOTING instead of staying in DISCUSSING.

        Raises:
            ValueError: if the motion does not exist.
            InvalidTransitionError: if the transition is not allowed.
        """
        motion = await self.storage.get_motion(motion_id)
        if motion is None:
            raise ValueError(f"Motion {motion_id} not found")

        old_status = motion["status"]

        # Special logic: round_complete may auto-promote to voting
        if (
            old_status == MotionStatus.DISCUSSING
            and event == "round_complete"
        ):
            current_round = motion["current_round"]
            total_rounds = motion["rounds"]
            if current_round >= total_rounds:
                new_status = MotionStatus.VOTING
            else:
                new_status = MotionStatus.DISCUSSING
        else:
            key = (old_status, event)
            if key not in _TRANSITIONS:
                raise InvalidTransitionError(
                    f"Invalid transition: {old_status} + {event}"
                )
            new_status = _TRANSITIONS[key]

        await self.storage.update_motion_status(motion_id, new_status.value)
        logger.info(
            "Motion %s: %s -> %s (event=%s)",
            motion_id, old_status, new_status.value, event,
        )
        return new_status

    async def can_speak(
        self, motion_id: str, agent_id: str
    ) -> bool:
        """Check whether an agent is allowed to speak on a motion.

        Conditions:
            - Motion exists and is in DISCUSSING status.
            - Agent is registered in the system.
        """
        motion = await self.storage.get_motion(motion_id)
        if motion is None or motion["status"] != MotionStatus.DISCUSSING:
            return False
        agent = await self.storage.get_agent(agent_id)
        return agent is not None

    async def can_vote(
        self, motion_id: str, agent_id: str
    ) -> bool:
        """Check whether an agent is allowed to vote on a motion.

        Conditions:
            - Motion exists and is in VOTING status.
            - Agent is registered in the system.
            - Agent has not already voted on this motion.
        """
        motion = await self.storage.get_motion(motion_id)
        if motion is None or motion["status"] != MotionStatus.VOTING:
            return False
        agent = await self.storage.get_agent(agent_id)
        if agent is None:
            return False
        if await self.storage.has_voted(motion_id, agent_id):
            return False
        return True
