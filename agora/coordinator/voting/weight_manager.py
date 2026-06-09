"""Weight manager for weighted voting in the Agora Coordinator.

Manages agent voting weights based on configurable strategies:
manual, expertise, or reputation-based weighting.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..storage import Storage

logger = logging.getLogger(__name__)


class WeightSource(str, Enum):
    """Origin of agent voting weights."""

    MANUAL = "manual"
    REPUTATION = "reputation"
    EXPERTISE = "expertise"
    STAKES = "stakes"


class WeightManager:
    """Manages agent voting weights per motion.

    Supports manual weights, expertise-based, and reputation-based
    strategies. Falls back to equal weighting (1.0) by default.
    """

    DEFAULT_WEIGHT = 1.0

    def __init__(self, storage: Storage, config: dict) -> None:
        self.storage = storage
        self.config = config
        self._weight_cache: dict[str, dict[str, float]] = {}

    async def get_weights(self, motion_id: str) -> dict[str, float]:
        """Retrieve agent weights for a motion (cached)."""
        if motion_id in self._weight_cache:
            return self._weight_cache[motion_id]

        strategy = self.config.get("weight_strategy")
        if strategy == WeightSource.MANUAL:
            weights = self._get_manual_weights()
        elif strategy == WeightSource.EXPERTISE:
            weights = await self._get_expertise_weights(motion_id)
        elif strategy == WeightSource.REPUTATION:
            weights = await self._get_reputation_weights()
        else:
            agents = await self.storage.list_agents()
            weights = {a["agent_id"]: self.DEFAULT_WEIGHT for a in agents}

        self._weight_cache[motion_id] = weights
        return weights

    def clear_cache(self, motion_id: str | None = None) -> None:
        """Invalidate weight cache for a motion or all motions."""
        if motion_id:
            self._weight_cache.pop(motion_id, None)
        else:
            self._weight_cache.clear()

    def _get_manual_weights(self) -> dict[str, float]:
        """Return manually configured weights from config."""
        return dict(self.config.get("manual_weights", {}))

    async def _get_expertise_weights(
        self, motion_id: str
    ) -> dict[str, float]:
        """Compute weights based on agent expertise overlap with motion."""
        motion = await self.storage.get_motion(motion_id)
        ctx = motion.get("context", "") if motion else ""
        domains = ctx.split(",") if ctx else []
        agents = await self.storage.list_agents()

        weights: dict[str, float] = {}
        for agent in agents:
            expertise = agent.get("capabilities", [])
            matching = len(set(expertise) & set(domains))
            weights[agent["agent_id"]] = (
                self.DEFAULT_WEIGHT + 0.5 * matching
            )
        return weights

    async def _get_reputation_weights(self) -> dict[str, float]:
        """Compute weights based on reputation (placeholder)."""
        agents = await self.storage.list_agents()
        # TODO: implement real reputation scoring
        return {a["agent_id"]: self.DEFAULT_WEIGHT for a in agents}
