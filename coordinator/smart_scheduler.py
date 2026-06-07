"""Smart discussion scheduler for the Agora Coordinator.

Uses QualityAssessor, ConsensusDetector, and DevilsAdvocateManager
to dynamically schedule discussion rounds based on quality metrics.
Phase 6.3: Integrates RealTimeEvaluator and ConsensusJumpManager.
"""
from __future__ import annotations

import logging
from typing import Optional

from .assessment import Assessment, AssessmentResult, ConsensusLevel, QualityAssessor
from .config import Settings
from .consensus_jump import ConsensusJumpManager
from .devils_advocate import DevilsAdvocateManager
from .dynamic_rounds import DynamicRoundManager, RoundConfig
from .realtime_evaluator import RealTimeEvaluator, RealTimeEvalResult
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
        self.realtime_evaluator = RealTimeEvaluator(
            storage,
            consensus_threshold=config.realtime_consensus_threshold,
            min_messages_for_consensus=config.realtime_min_messages,
        )
        self.consensus_jump = ConsensusJumpManager(
            storage,
            consensus_ratio=config.consensus_jump_ratio,
        )
        self.dynamic_rounds = DynamicRoundManager(
            RoundConfig(
                min_rounds=config.dynamic_min_rounds,
                max_rounds=config.dynamic_max_rounds,
                adaptive=config.dynamic_adaptive,
                quality_threshold=config.dynamic_quality_threshold,
                low_quality_threshold=config.dynamic_low_quality_threshold,
            )
        )

    async def on_message(
        self, motion_id: str, message: dict,
    ) -> Optional[RealTimeEvalResult]:
        """Evaluate after each message for instant consensus or early end."""
        if not self.config.smart_discussion_enabled:
            return None
        result = await self.realtime_evaluator.on_message(
            motion_id, message,
        )
        if result is None:
            return None

        if result.type == "INSTANT_CONSENSUS":
            await self._handle_instant_consensus(motion_id, result)
        elif result.type == "EARLY_TERMINATION":
            await self._transition_to_voting(motion_id)

        return result

    async def _handle_instant_consensus(
        self, motion_id: str, result: RealTimeEvalResult,
    ) -> None:
        """Handle instant consensus detected by realtime evaluator."""
        await self.ws_manager.broadcast({
            "type": "INSTANT_CONSENSUS",
            "motion_id": motion_id,
            "payload": {
                "topic": result.consensus_topic,
                "level": result.consensus_level.value,
                "action": result.action,
            },
        })
        logger.info(
            "Motion %s: instant consensus on %s",
            motion_id, result.consensus_topic,
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
        # Use consensus jump to find unresolved sub-topics
        focus = await self.consensus_jump.get_focus_topics(motion_id)
        key_points = assessment.metrics.key_points_identified[:3]
        unresolved = assessment.metrics.unresolved_points[:3]

        # Merge consensus-jump focus with assessment focus
        combined_focus = list(dict.fromkeys(focus + key_points + unresolved))

        await self.ws_manager.broadcast({
            "type": "TOPIC_REDIRECT",
            "motion_id": motion_id,
            "payload": {
                "message": "讨论偏离主题，请聚焦于：",
                "focus_areas": combined_focus[:5],
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
        """Continue to next round using dynamic round management."""
        motion = await self.storage.get_motion(motion_id)
        if motion is None:
            return

        # Consensus jump: skip rounds if all sub-topics agreed
        if self.config.smart_discussion_enabled:
            consensus_topics = await (
                self.consensus_jump.get_consensus_topics(motion_id)
            )
            focus_topics = await (
                self.consensus_jump.get_focus_topics(motion_id)
            )
            if consensus_topics and not focus_topics:
                logger.info(
                    "Motion %s: consensus jump, all topics agreed",
                    motion_id,
                )
                await self._transition_to_voting(motion_id)
                return

        # Dynamic rounds: check if discussion should continue
        if self.config.dynamic_rounds_enabled:
            assessment = await self.quality_assessor.assess(
                motion_id, self.storage,
            )
            quality = 0.0
            if assessment.metrics.quality_score:
                quality = assessment.metrics.quality_score.overall

            cont, reason = await self.dynamic_rounds.should_continue(
                motion_id, self.storage,
                quality, assessment.consensus_level,
            )
            if not cont:
                logger.info(
                    "Motion %s: dynamic rounds stop (%s)",
                    motion_id, reason,
                )
                await self._transition_to_voting(motion_id)
                return
            logger.info(
                "Motion %s: dynamic rounds continue (%s)",
                motion_id, reason,
            )
        elif motion.get("current_round", 0) >= self.config.max_rounds:
            await self._transition_to_voting(motion_id)
            return

        current = motion.get("current_round", 0)
        await self.storage.increment_round(motion_id)
        await self.ws_manager.broadcast({
            "type": "ROUND_COMPLETE",
            "motion_id": motion_id,
            "payload": {
                "round": current,
                "next_round": current + 1,
            },
        })
