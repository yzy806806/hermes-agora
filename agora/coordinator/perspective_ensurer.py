"""Perspective diversity ensurer (Phase 6.5).

Ensures discussions have diverse perspectives by detecting
missing stances and recommending role supplements.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .models import DiscussionRole

if TYPE_CHECKING:
    from .storage.storage import Storage

logger = logging.getLogger(__name__)


class PerspectiveEnsurer:
    """Ensures perspective diversity in discussions."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    async def ensure_diversity(
        self, motion_id: str, assignments: dict[str, DiscussionRole]
    ) -> list[DiscussionRole]:
        """Check discussion for missing perspectives, return needed roles."""
        messages = await self.storage.get_messages(motion_id)
        needed: list[DiscussionRole] = []

        if not messages:
            # No messages yet — need all perspectives
            return [
                DiscussionRole.SUPPORT_ADVOCATE,
                DiscussionRole.OPPOSE_ADVOCATE,
                DiscussionRole.NEUTRAL,
            ]

        stances = [m.get("stance", "neutral") for m in messages]

        if stances.count("support") == 0:
            needed.append(DiscussionRole.SUPPORT_ADVOCATE)
        if stances.count("oppose") == 0:
            needed.append(DiscussionRole.OPPOSE_ADVOCATE)
        if stances.count("neutral") < len(messages) * 0.2:
            needed.append(DiscussionRole.NEUTRAL)

        logger.info(
            "Perspective check for motion %s: need roles %s", motion_id, needed
        )
        return needed

    async def get_stance_distribution(self, motion_id: str) -> dict[str, int]:
        """Get current stance distribution for a motion."""
        messages = await self.storage.get_messages(motion_id)
        dist: dict[str, int] = {"support": 0, "oppose": 0, "neutral": 0}
        for msg in messages:
            stance = msg.get("stance", "neutral")
            if stance in dist:
                dist[stance] += 1
        return dist
