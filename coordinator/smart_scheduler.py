"""Smart discussion scheduler for the Agora Coordinator.

Uses QualityAssessor, ConsensusDetector, and DevilsAdvocateManager
to dynamically schedule discussion rounds based on quality metrics.
"""
from __future__ import annotations

import logging

from .assessment import Assessment, AssessmentResult, QualityAssessor
from .config import Settings
from .devils_advocate import DevilsAdvocateManager
from .state import StateMachine
from .storage import Storage
from .ws import ConnectionManager

logger = logging.getLogger(__name__)


class SmartDiscussionScheduler:
    """Intelligent discussion scheduler that assesses quality and
    dynamically decides whether to continue, redirect, trigger
    devil's advocate, or proceed to voting.
    """

    def __init__(
        self,
        storage: Storage,
        ws_manager: ConnectionManager,
        state_machine: StateMachine,
        config: Settings,
    ) -> None:
        self.storage = storage
        self.ws_manager = ws_manager
        self.state_machine = state_machine
        self.config = config
        self.quality_assessor = QualityAssessor()
        self.devils_advocate = DevilsAdvocateManager(
            storage, ws_manager,
        )

    async def should_assess(
        self, motion_id: str, current_round: int
    ) -> bool:
        """Check if assessment should run after current round."""
        if not self.config.smart_discussion_enabled:
            return False
        messages = await self.storage.get_messages(motion_id)
        round_msgs = [
            m for m in messages if m.get("round") == current_round
        ]
        agents = await self.storage.list_agents()
        spoken = {m.get("agent_id") for m in round_msgs}
        return len(spoken) >= len(agents)

    async def run_assessment(self, motion_id: str) -> None:
        """Run assessment and act on the result."""
        assessment = await self.quality_assessor.assess(
            motion_id, self.storage,
        )
        await self._broadcast_assessment(motion_id, assessment)
        await self._act_on_assessment(motion_id, assessment)

    async def _broadcast_assessment(
        self, motion_id: str, assessment: Assessment,
    ) -> None:
        """Broadcast assessment result to all connected agents."""
        await self.ws_manager.broadcast({
            "type": "ASSESSMENT",
            "motion_id": motion_id,
            "payload": {
                "result": assessment.result.value,
                "consensus_level": assessment.consensus_level.value,
                "metrics": {
                    "total_messages": assessment.metrics.total_messages,
                    "argument_quality": (
                        assessment.metrics.argument_quality_score
                    ),
                    "topic_relevance": (
                        assessment.metrics.topic_relevance_score
                    ),
                },
                "rationale": assessment.rationale,
                "recommendations": assessment.recommendations,
            },
        })

    async def _act_on_assessment(
        self, motion_id: str, assessment: Assessment,
    ) -> None:
        """Take action based on assessment result."""
        result = assessment.result
        if result in (
            AssessmentResult.CONSENSUS_REACHED,
            AssessmentResult.SUFFICIENT,
        ):
            await self._transition_to_voting(motion_id)
        elif result == AssessmentResult.OFF_TOPIC:
            await self._redirect_discussion(motion_id, assessment)
        elif result == AssessmentResult.DEVILS_ADVOCATE:
            await self._trigger_devils_advocate(motion_id)
        else:
            await self._continue_next_round(motion_id)

    async def _transition_to_voting(
        self, motion_id: str,
    ) -> None:
        """Move motion from ASSESSING to VOTING."""
        await self.state_machine.transition(motion_id, "start_voting")
        logger.info("Motion %s: early vote triggered", motion_id)

    async def _redirect_discussion(
        self, motion_id: str, assessment: Assessment,
    ) -> None:
        """Redirect off-topic discussion back to focus areas."""
        await self.ws_manager.broadcast({
            "type": "TOPIC_REDIRECT",
            "motion_id": motion_id,
            "payload": {
                "message": "讨论偏离主题，请聚焦于：",
                "focus_areas": (
                    assessment.metrics.key_points_identified[:3]
                ),
                "unresolved_points": (
                    assessment.metrics.unresolved_points[:3]
                ),
            },
        })
        await self.state_machine.transition(
            motion_id, "assessment_done",
        )
        await self._continue_next_round(motion_id)

    async def _trigger_devils_advocate(
        self, motion_id: str,
    ) -> None:
        """Trigger devil's advocate for one-sided discussions."""
        should, agent_id = await self.devils_advocate.should_trigger(
            motion_id,
        )
        if should and agent_id:
            await self.state_machine.transition(
                motion_id, "needs_devils_advocate",
            )
            await self.devils_advocate.trigger(motion_id, agent_id)
            logger.info(
                "Motion %s: devil's advocate -> agent %s",
                motion_id, agent_id,
            )
        else:
            await self.state_machine.transition(
                motion_id, "assessment_done",
            )
            await self._continue_next_round(motion_id)

    async def complete_devils_advocate(
        self, motion_id: str,
    ) -> None:
        """Called when devil's advocate phase is done."""
        await self.state_machine.transition(
            motion_id, "devils_advocate_done",
        )
        await self._continue_next_round(motion_id)

    async def _continue_next_round(
        self, motion_id: str,
    ) -> None:
        """Continue to next discussion round or force voting."""
        motion = await self.storage.get_motion(motion_id)
        if motion is None:
            return
        current = motion.get("current_round", 0)
        if current >= self.config.max_rounds:
            await self._transition_to_voting(motion_id)
        else:
            await self.storage.increment_round(motion_id)
            await self.ws_manager.broadcast({
                "type": "ROUND_COMPLETE",
                "motion_id": motion_id,
                "payload": {
                    "round": current,
                    "next_round": current + 1,
                },
            })
