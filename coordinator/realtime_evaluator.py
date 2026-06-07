"""Real-time evaluator for instant consensus detection.

Evaluates each message as it arrives to detect early consensus opportunities
and determine if discussion can skip remaining rounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .assessment import ConsensusLevel

if TYPE_CHECKING:
    from .storage import Storage


@dataclass
class RealTimeEvalResult:
    """Result from real-time evaluation."""
    type: str  # INSTANT_CONSENSUS, EARLY_TERMINATION, CONTINUE
    consensus_topic: Optional[str] = None
    consensus_level: ConsensusLevel = ConsensusLevel.LOW
    action: Optional[str] = None
    reason: Optional[str] = None


class RealTimeEvaluator:
    """Real-time evaluator - checks after each message."""

    def __init__(
        self,
        storage: Storage,
        consensus_threshold: float = 0.8,
        min_messages_for_consensus: int = 3,
    ) -> None:
        self.storage = storage
        self.consensus_threshold = consensus_threshold
        self.min_messages = min_messages_for_consensus

    async def on_message(
        self, motion_id: str, message: dict,
    ) -> Optional[RealTimeEvalResult]:
        """Evaluate after each message, return result if action needed."""
        messages = await self.storage.get_messages(motion_id)
        messages = list(messages) + [message]  # include new message

        # Quick consensus detection
        consensus, level = self._detect_instant_consensus(messages)
        if consensus:
            return RealTimeEvalResult(
                type="INSTANT_CONSENSUS",
                consensus_topic=consensus,
                consensus_level=level,
                action="SKIP_NEXT_ROUNDS",
            )

        # Check for early termination
        if self._should_end_early(messages):
            return RealTimeEvalResult(
                type="EARLY_TERMINATION",
                reason="quality_sufficient",
                action="PROCEED_TO_VOTING",
            )

        return None

    def _detect_instant_consensus(
        self, messages: list[dict],
    ) -> tuple[Optional[str], ConsensusLevel]:
        """Detect instant consensus based on stance distribution."""
        stances = [m.get("stance") for m in messages if m.get("stance")]
        total = len(stances)
        if total < self.min_messages:
            return None, ConsensusLevel.LOW

        support_count = stances.count("support")
        oppose_count = stances.count("oppose")

        if support_count / total >= self.consensus_threshold:
            return "main_topic", ConsensusLevel.HIGH
        if oppose_count / total >= self.consensus_threshold:
            return "main_topic", ConsensusLevel.HIGH

        return None, ConsensusLevel.LOW

    def _should_end_early(self, messages: list[dict]) -> bool:
        """Determine if discussion should end early."""
        if len(messages) < 6:
            return False

        # Check quality indicators
        has_evidence = sum(1 for m in messages if m.get("evidence"))
        evidence_ratio = has_evidence / len(messages)
        if evidence_ratio < 0.3:
            return False

        # Check average message length
        avg_len = sum(len(m.get("content", "")) for m in messages) / len(messages)
        if avg_len < 100:
            return False

        return True
