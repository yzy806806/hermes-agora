"""Multi-dimensional quality scorer for discussion assessment.

Provides QualityScore dataclass and QualityScorer class for evaluating
discussion quality across multiple dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass

from .storage import Storage


@dataclass
class QualityScore:
    """Multi-dimensional quality score for a discussion.

    Attributes:
        evidence_sufficiency: Evidence support ratio (0.0-1.0).
        argument_logic: Argument quality based on length/structure (0.0-1.0).
        perspective_diversity: Diversity of stances (0.0-1.0).
        rebuttal_strength: Rebuttal engagement via reply_to (0.0-1.0).
        overall: Weighted composite score (0.0-1.0).
    """

    evidence_sufficiency: float
    argument_logic: float
    perspective_diversity: float
    rebuttal_strength: float
    overall: float


class QualityScorer:
    """Multi-dimensional quality scorer for discussions."""

    async def score(self, motion_id: str, storage: Storage) -> QualityScore:
        """Calculate multi-dimensional quality score for a motion.

        Args:
            motion_id: ID of the motion to score.
            storage: Storage instance for fetching messages.

        Returns:
            QualityScore with all dimension scores and overall.
        """
        messages = await storage.get_messages(motion_id)

        evidence = self._score_evidence(messages)
        logic = self._score_logic(messages)
        diversity = self._score_diversity(messages)
        rebuttal = self._score_rebuttal(messages)

        overall = (
            evidence * 0.3
            + logic * 0.3
            + diversity * 0.2
            + rebuttal * 0.2
        )

        return QualityScore(
            evidence_sufficiency=evidence,
            argument_logic=logic,
            perspective_diversity=diversity,
            rebuttal_strength=rebuttal,
            overall=overall,
        )

    def _score_evidence(self, messages: list[dict]) -> float:
        """Score evidence sufficiency (ratio of messages with evidence)."""
        if not messages:
            return 0.0
        has_evidence = sum(1 for m in messages if m.get("evidence"))
        return min(has_evidence / len(messages), 1.0)

    def _score_logic(self, messages: list[dict]) -> float:
        """Score argument logic based on average content length."""
        if not messages:
            return 0.0
        avg_len = sum(len(m.get("content", "")) for m in messages) / len(messages)
        return min(avg_len / 200, 1.0)

    def _score_diversity(self, messages: list[dict]) -> float:
        """Score perspective diversity (unique stances, max 3 for full score)."""
        stances = {m.get("stance") for m in messages if m.get("stance")}
        return min(len(stances) / 3, 1.0)

    def _score_rebuttal(self, messages: list[dict]) -> float:
        """Score rebuttal strength (ratio of messages with reply_to)."""
        if not messages:
            return 0.0
        has_reply = sum(1 for m in messages if m.get("reply_to"))
        return min(has_reply / len(messages), 1.0)
