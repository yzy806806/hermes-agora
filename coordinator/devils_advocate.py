"""Devil's advocate mechanism — forces opposing views when discussion is one-sided."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .models import Stance
from .storage import Storage
from .ws import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class DevilsAdvocateConfig:
    """Configuration for the devil's advocate mechanism."""
    enabled: bool = True
    trigger_threshold: float = 0.7  # support ratio to trigger
    max_triggers_per_motion: int = 2


class DevilsAdvocateManager:
    """Manages devil's advocate triggers for motions."""

    def __init__(self, storage: Storage, ws_manager: ConnectionManager,
                 config: DevilsAdvocateConfig | None = None) -> None:
        self.storage = storage
        self.ws_manager = ws_manager
        self.config = config or DevilsAdvocateConfig()
        self._trigger_count: dict[str, int] = {}

    async def should_trigger(self, motion_id: str) -> tuple[bool, Optional[str]]:
        """Check if devil's advocate should trigger. Returns (should, agent_id)."""
        if not self.config.enabled:
            return False, None
        if self._trigger_count.get(motion_id, 0) >= self.config.max_triggers_per_motion:
            return False, None

        messages = await self.storage.get_messages(motion_id)
        if len(messages) < 3:
            return False, None

        counts: dict[str, int] = {}
        for m in messages:
            counts[m.get("stance", "")] = counts.get(m.get("stance", ""), 0) + 1
        total = sum(counts.values())
        if total == 0 or counts.get(Stance.SUPPORT, 0) / total < self.config.trigger_threshold:
            return False, None

        opposed = {m["agent_id"] for m in messages if m.get("stance") == Stance.OPPOSE}
        all_ids = {a["agent_id"] for a in await self.storage.list_agents()}
        potential = all_ids - opposed
        return (True, next(iter(potential))) if potential else (False, None)

    async def trigger(self, motion_id: str, target_agent_id: str) -> None:
        """Send devil's advocate request to the target agent."""
        self._trigger_count[motion_id] = self._trigger_count.get(motion_id, 0) + 1
        motion = await self.storage.get_motion(motion_id)
        if motion is None:
            logger.warning("Motion %s not found for devil's advocate", motion_id)
            return
        await self.ws_manager.send(target_agent_id, {
            "type": "DEVILS_ADVOCATE_REQUEST", "motion_id": motion_id,
            "payload": {
                "round": motion.get("current_round", 0) + 1,
                "topic": motion.get("title", ""),
                "description": motion.get("description", ""),
                "instruction": "请从反对角度提出你的观点和质疑，确保讨论的全面性。",
            },
        })
        logger.info("Devil's advocate: motion %s -> agent %s (count=%d)",
                     motion_id, target_agent_id, self._trigger_count[motion_id])
