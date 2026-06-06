"""Discussion Curator — optimizes motion config and post-discussion review.

Integrates history_pattern, judgment_tracker, and similar_topic modules
to provide smart discussion strategy optimization.
"""

from __future__ import annotations

import logging
from typing import Optional

from .history_pattern import HistoryPattern
from .judgment_tracker import JudgmentTracker
from .similar_topic import SimilarTopicDetector

logger = logging.getLogger(__name__)


class DiscussionCurator:
    """Discussion strategy optimizer combining all Phase 3 modules."""

    def __init__(
        self,
        storage,
        db_path: str,
        memory_path: str = "~/.hermes/memories/discussion_conclusions",
    ) -> None:
        self.storage = storage
        self.history_pattern = HistoryPattern(storage, db_path)
        self.judgment_tracker = JudgmentTracker(db_path)
        self.similar_detector = SimilarTopicDetector(memory_path)

    async def optimize_motion(self, motion: dict) -> dict:
        """Optimize a motion's configuration before creation.

        Uses history patterns and similar topics to suggest strategy,
        round count, and weighted voters.
        """
        title = motion.get("title", "")

        # 1. Get history pattern suggestion
        strategy = await self.history_pattern.suggest_strategy(title)

        # 2. Find similar historical conclusions
        reference_context = (
            await self.similar_detector.generate_reference_context(title)
        )

        # 3. Merge into optimized config
        optimized = {
            **motion,
            "suggested_rounds": strategy.get(
                "suggested_rounds", motion.get("rounds", 3)
            ),
            "strategy": strategy.get("strategy", "standard"),
            "reference_context": reference_context,
            "recommendations": strategy.get("recommendations", []),
        }

        # 4. For low-consensus topics, mark top performers for weighting
        if strategy.get("expected_consensus") == "low":
            top_performers = await self.judgment_tracker.get_leaderboard(3)
            optimized["weighted_voters"] = [
                p.agent_id for p in top_performers
            ]

        return optimized

    async def post_discussion_review(self, motion_id: str) -> dict:
        """Post-discussion review: record judgment accuracy per voter.

        Compares each voter's prediction against the actual decision.
        """
        motion = await self.storage.get_motion(motion_id)
        if not motion:
            return {"motion_id": motion_id, "error": "not_found"}

        votes = await self.storage.get_votes(motion_id)
        actual_decision = motion.get("decision", "no_consensus")

        for vote in votes:
            await self.judgment_tracker.record_vote(
                motion_id=motion_id,
                agent_id=vote["agent_id"],
                predicted_outcome=vote["vote"],
                actual_outcome=actual_decision,
                confidence=vote.get("confidence", 1.0),
            )

        return {
            "motion_id": motion_id,
            "decision": actual_decision,
            "participants_evaluated": len(votes),
        }
