"""Consensus jump mechanism for skipping settled sub-topics.

Analyzes sub-topic consensus states so the scheduler can skip
discussion of already-agreed points and focus on unresolved areas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Storage


@dataclass
class SubTopicConsensus:
    """Consensus state for a sub-topic."""
    topic: str
    consensus_reached: bool
    supporting_agents: list[str] = field(default_factory=list)
    opposing_agents: list[str] = field(default_factory=list)
    support_ratio: float = 0.0


class ConsensusJumpManager:
    """Manages consensus point jumping for efficient discussions."""

    def __init__(self, storage: Storage, consensus_ratio: float = 0.7) -> None:
        self.storage = storage
        self.consensus_ratio = consensus_ratio
        self._consensus_cache: dict[str, list[SubTopicConsensus]] = {}

    async def analyze_sub_topics(
        self, motion_id: str,
    ) -> list[SubTopicConsensus]:
        """Analyze sub-topic consensus states from messages."""
        messages = await self.storage.get_messages(motion_id)

        # Group by stance
        by_stance: dict[str, list[str]] = {
            "support": [], "oppose": [], "neutral": [],
        }
        for msg in messages:
            s = msg.get("stance", "neutral")
            if s in by_stance:
                by_stance[s].append(msg.get("agent_id", ""))

        total = sum(len(v) for v in by_stance.values())
        if total == 0:
            return []

        results = []
        for stance, agents in by_stance.items():
            if not agents:
                continue  # skip empty stances
            ratio = len(agents) / total
            reached = ratio >= self.consensus_ratio and len(agents) >= 2
            results.append(SubTopicConsensus(
                topic=f"stance_{stance}",
                consensus_reached=reached,
                supporting_agents=agents,
                support_ratio=ratio,
            ))

        self._consensus_cache[motion_id] = results
        return results

    async def get_focus_topics(
        self, motion_id: str,
    ) -> list[str]:
        """Get sub-topics that still need discussion."""
        sub_topics = await self.analyze_sub_topics(motion_id)
        return [s.topic for s in sub_topics if not s.consensus_reached]

    async def get_consensus_topics(
        self, motion_id: str,
    ) -> list[str]:
        """Get sub-topics where consensus is already reached."""
        sub_topics = await self.analyze_sub_topics(motion_id)
        return [s.topic for s in sub_topics if s.consensus_reached]

    def clear_cache(self, motion_id: str | None = None) -> None:
        """Clear consensus cache for a motion or all."""
        if motion_id:
            self._consensus_cache.pop(motion_id, None)
        else:
            self._consensus_cache.clear()
