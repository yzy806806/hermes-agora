"""Judgment accuracy tracker for Agora participants.

Tracks each agent's vote prediction accuracy and provides
weighted voting based on historical correctness.
"""

from __future__ import annotations

import logging
from typing import Optional

from .judgment_types import AgentScore
from .storage.storage import Storage

logger = logging.getLogger(__name__)


class JudgmentTracker:
    """Participant judgment accuracy tracker."""

    def __init__(self, storage: Storage) -> None:
        self._storage = storage
        self._score_cache: dict[str, AgentScore] = {}

    async def record_vote(
        self, motion_id: str, agent_id: str,
        predicted_outcome: str, actual_outcome: str,
        confidence: float,
    ) -> int:
        """Record a vote prediction and its actual outcome."""
        record_id = await self._storage.record_judgment(
            motion_id, agent_id,
            predicted_outcome, actual_outcome, confidence)
        await self._update_cache(agent_id)
        return record_id

    async def get_agent_score(
        self, agent_id: str,
    ) -> AgentScore:
        """Get the accuracy score for an agent."""
        if agent_id in self._score_cache:
            return self._score_cache[agent_id]
        await self._update_cache(agent_id)
        return self._score_cache.get(agent_id, AgentScore(agent_id=agent_id))

    async def _update_cache(self, agent_id: str) -> None:
        """Refresh the cached score for an agent from the DB."""
        stats = await self._storage.get_agent_stats(agent_id)
        if stats is None:
            self._score_cache[agent_id] = AgentScore(agent_id=agent_id)
            return
        total = stats["total"]
        correct = stats["correct"] or 0
        accuracy = correct / total if total > 0 else 0.0
        trend = await self._storage.get_recent_trend(agent_id)
        self._score_cache[agent_id] = AgentScore(
            agent_id=agent_id,
            total_decisions=total,
            correct_predictions=correct,
            accuracy=accuracy,
            avg_confidence=stats["avg_conf"] or 0.0,
            recent_trend=trend,
        )

    async def get_weighted_vote(
        self, agent_id: str,
    ) -> float:
        """Get vote weight for an agent based on accuracy.

        New agents (<3 decisions) get default weight 1.0.
        Otherwise weight ranges from 0.5 to 1.0 by accuracy.
        """
        score = await self.get_agent_score(agent_id)
        if score.total_decisions < 3:
            return 1.0
        return 0.5 + (score.accuracy * 0.5)

    async def get_leaderboard(
        self, limit: int = 10,
    ) -> list[AgentScore]:
        """Get agents ranked by prediction accuracy."""
        rows = await self._storage.get_judgment_leaderboard(limit)
        results: list[AgentScore] = []
        for row in rows:
            total = row["total"]
            correct = row["correct"] or 0
            results.append(AgentScore(
                agent_id=row["agent_id"],
                total_decisions=total,
                correct_predictions=correct,
                accuracy=correct / total if total > 0 else 0.0,
            ))
        return results
