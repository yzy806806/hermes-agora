"""Dynamic round management for the Agora Coordinator.

Provides RoundConfig and DynamicRoundManager to adaptively control
discussion round count based on quality and consensus.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .assessment import ConsensusLevel

if TYPE_CHECKING:
    from .storage import Storage

logger = logging.getLogger(__name__)


@dataclass
class RoundConfig:
    """Dynamic round configuration.

    Attributes:
        min_rounds: Minimum rounds before early termination is allowed.
        max_rounds: Hard cap on discussion rounds.
        adaptive: If True, extend rounds when quality is low.
        quality_threshold: Quality score above which early exit is allowed.
        low_quality_threshold: Quality score below which rounds are extended.
    """

    min_rounds: int = 2
    max_rounds: int = 5
    adaptive: bool = True
    quality_threshold: float = 0.7
    low_quality_threshold: float = 0.4


class DynamicRoundManager:
    """Manages dynamic round decisions based on quality and consensus.

    Determines whether a discussion should continue to another round,
    end early due to consensus/quality, or be extended when quality
    is still low.
    """

    def __init__(self, config: RoundConfig | None = None) -> None:
        self.config = config or RoundConfig()

    async def should_continue(
        self,
        motion_id: str,
        storage: Storage,
        quality_score: float,
        consensus_level: ConsensusLevel,
    ) -> tuple[bool, str]:
        """Decide if the discussion should continue to the next round.

        Args:
            motion_id: ID of the motion under discussion.
            storage: Storage instance to fetch motion state.
            quality_score: Current quality score (0.0-1.0).
            consensus_level: Current consensus level.

        Returns:
            Tuple of (should_continue: bool, reason: str).
        """
        motion = await storage.get_motion(motion_id)
        if motion is None:
            return False, "motion_not_found"

        current_round = motion.get("current_round", 0)

        # 1. Must meet minimum rounds before considering early exit
        if current_round < self.config.min_rounds:
            return True, "min_rounds_not_met"

        # 2. High consensus reached — stop early
        if consensus_level == ConsensusLevel.HIGH:
            return False, "consensus_reached"

        # 3. Quality sufficient and minimum rounds met — stop
        if quality_score >= self.config.quality_threshold:
            return False, "quality_sufficient"

        # 4. Hard cap reached — force stop
        if current_round >= self.config.max_rounds:
            return False, "max_rounds_reached"

        # 5. Adaptive: extend when quality is still low
        if self.config.adaptive and quality_score < self.config.low_quality_threshold:
            logger.info(
                "Motion %s: quality %.2f below threshold, extending rounds",
                motion_id, quality_score,
            )
            return True, "quality_low_extend"

        return True, "continue"
