"""Smart discussion assessment module.

Provides consensus detection and quality assessment for intelligent
discussion scheduling decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .models import Stance

if TYPE_CHECKING:
    from .storage import Storage


class ConsensusLevel(str, Enum):
    """Consensus level based on stance distribution."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    FRACTURED = "fractured"


class AssessmentResult(str, Enum):
    """Assessment decision result."""
    CONSENSUS_REACHED = "consensus_reached"
    SUFFICIENT = "sufficient"
    NEEDS_MORE = "needs_more"
    OFF_TOPIC = "off_topic"
    DEVILS_ADVOCATE = "devils_advocate"


@dataclass
class DiscussionMetrics:
    """Discussion quality metrics."""
    total_messages: int
    stance_distribution: dict[Stance, int]
    argument_quality_score: float
    topic_relevance_score: float
    key_points_identified: list[str] = field(default_factory=list)
    unresolved_points: list[str] = field(default_factory=list)


@dataclass
class Assessment:
    """Assessment result with rationale."""
    result: AssessmentResult
    consensus_level: ConsensusLevel
    metrics: DiscussionMetrics
    rationale: str
    recommendations: list[str] = field(default_factory=list)


class ConsensusDetector:
    """Detects consensus level from message stance distribution."""

    def detect(self, messages: list[dict]) -> tuple[ConsensusLevel, dict[Stance, int]]:
        """Detect consensus level from messages."""
        if not messages:
            return ConsensusLevel.LOW, {}

        stance_counts: dict[Stance, int] = {}
        for msg in messages:
            stance = msg.get("stance")
            if stance:
                stance_counts[stance] = stance_counts.get(stance, 0) + 1

        total = sum(stance_counts.values())
        if total == 0:
            return ConsensusLevel.LOW, {}

        support_ratio = stance_counts.get(Stance.SUPPORT, 0) / total
        oppose_ratio = stance_counts.get(Stance.OPPOSE, 0) / total

        if support_ratio >= 0.7:
            return ConsensusLevel.HIGH, stance_counts
        elif support_ratio >= 0.5 or oppose_ratio >= 0.5:
            return ConsensusLevel.MODERATE, stance_counts
        elif support_ratio > 0.3 and oppose_ratio > 0.3:
            return ConsensusLevel.FRACTURED, stance_counts
        return ConsensusLevel.LOW, stance_counts


class QualityAssessor:
    """Assesses discussion quality and makes scheduling decisions."""

    async def assess(self, motion_id: str, storage: Storage) -> Assessment:
        """Assess discussion quality for a motion."""
        messages = await storage.get_messages(motion_id)
        motion = await storage.get_motion(motion_id)
        topic = motion.get("title", "") if motion else ""

        detector = ConsensusDetector()
        consensus_level, stance_counts = detector.detect(messages)

        quality_score = self._assess_argument_quality(messages)
        relevance_score = self._assess_topic_relevance(messages, topic)
        key_points = self._extract_key_points(messages)
        unresolved = self._identify_unresolved(messages)

        metrics = DiscussionMetrics(
            total_messages=len(messages),
            stance_distribution=stance_counts,
            argument_quality_score=quality_score,
            topic_relevance_score=relevance_score,
            key_points_identified=key_points,
            unresolved_points=unresolved,
        )
        return self._make_decision(consensus_level, metrics, len(messages))

    def _assess_argument_quality(self, messages: list[dict]) -> float:
        """Evaluate argument quality based on evidence and length."""
        if not messages:
            return 0.0
        total_evidence = sum(len(m.get("evidence", [])) for m in messages)
        avg_length = sum(len(m.get("content", "")) for m in messages) / len(messages)
        evidence_score = min(total_evidence / max(len(messages), 1), 1.0)
        length_score = min(avg_length / 200, 1.0)
        return evidence_score * 0.6 + length_score * 0.4

    def _assess_topic_relevance(self, messages: list[dict], topic: str) -> float:
        """Evaluate topic relevance (placeholder)."""
        return 0.8

    def _extract_key_points(self, messages: list[dict]) -> list[str]:
        """Extract key points (placeholder)."""
        return []

    def _identify_unresolved(self, messages: list[dict]) -> list[str]:
        """Identify unresolved points (placeholder)."""
        return []

    def _make_decision(
        self, level: ConsensusLevel, metrics: DiscussionMetrics, count: int
    ) -> Assessment:
        """Make assessment decision based on metrics."""
        min_messages = 6

        if level == ConsensusLevel.HIGH:
            return Assessment(
                result=AssessmentResult.CONSENSUS_REACHED,
                consensus_level=level,
                metrics=metrics,
                rationale="High consensus detected",
                recommendations=["Proceed to voting"],
            )

        if level == ConsensusLevel.FRACTURED and metrics.argument_quality_score < 0.5:
            return Assessment(
                result=AssessmentResult.NEEDS_MORE,
                consensus_level=level,
                metrics=metrics,
                rationale="Severe disagreement with weak arguments",
                recommendations=["Continue discussion", "Add more evidence"],
            )

        if metrics.topic_relevance_score < 0.5:
            return Assessment(
                result=AssessmentResult.OFF_TOPIC,
                consensus_level=level,
                metrics=metrics,
                rationale="Discussion off topic",
                recommendations=["Refocus on topic"],
            )

        if count >= min_messages and metrics.argument_quality_score >= 0.5:
            return Assessment(
                result=AssessmentResult.SUFFICIENT,
                consensus_level=level,
                metrics=metrics,
                rationale="Discussion sufficient",
                recommendations=["Proceed to voting"],
            )

        return Assessment(
            result=AssessmentResult.NEEDS_MORE,
            consensus_level=level,
            metrics=metrics,
            rationale="Discussion not yet sufficient",
            recommendations=["Continue next round"],
        )
