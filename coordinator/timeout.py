"""Discussion timeout handling for the Agora Coordinator service."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class TimeoutAction(str, Enum):
    """Actions to take when a timeout fires."""
    FORCE_VOTE = "force_vote"
    END_DISCUSSION = "end_discussion"
    EXTEND_ROUND = "extend_round"

@dataclass
class TimeoutConfig:
    """Configuration for discussion timeouts."""
    round_timeout: int = 300
    vote_timeout: int = 120
    discussion_timeout: int = 1800

class TimeoutManager:
    """Manages discussion and voting timeouts via asyncio tasks."""

    def __init__(
        self,
        config: Optional[TimeoutConfig] = None,
        on_timeout: Optional[Callable[[str, TimeoutAction], Awaitable[None]]] = None,
    ) -> None:
        self.config = config or TimeoutConfig()
        self.on_timeout = on_timeout
        self._timers: dict[str, asyncio.Task] = {}
        self._start_times: dict[str, float] = {}
        self._durations: dict[str, int] = {}
        self._actions: dict[str, TimeoutAction] = {}

    def start_round_timeout(self, motion_id: str, timeout_seconds: Optional[int] = None) -> None:
        duration = timeout_seconds or self.config.round_timeout
        self._start_timer(motion_id, duration, TimeoutAction.FORCE_VOTE)

    def start_vote_timeout(self, motion_id: str, timeout_seconds: Optional[int] = None) -> None:
        duration = timeout_seconds or self.config.vote_timeout
        self._start_timer(motion_id, duration, TimeoutAction.END_DISCUSSION)

    def cancel_timeout(self, motion_id: str) -> None:
        if motion_id in self._timers:
            self._timers[motion_id].cancel()
            for store in (self._timers, self._start_times, self._durations, self._actions):
                store.pop(motion_id, None)

    def get_remaining_time(self, motion_id: str) -> Optional[int]:
        if motion_id not in self._start_times:
            return None
        elapsed = time.time() - self._start_times[motion_id]
        return max(0, int(self._durations[motion_id] - elapsed))

    async def handle_timeout(self, motion_id: str) -> TimeoutAction:
        action = self._actions.get(motion_id, TimeoutAction.FORCE_VOTE)
        logger.info("Timeout fired for motion %s, action: %s", motion_id, action)
        if self.on_timeout:
            await self.on_timeout(motion_id, action)
        return action

    def _start_timer(self, motion_id: str, duration: int, action: TimeoutAction) -> None:
        self.cancel_timeout(motion_id)
        self._start_times[motion_id] = time.time()
        self._durations[motion_id] = duration
        self._actions[motion_id] = action

        async def timer() -> None:
            try:
                await asyncio.sleep(duration)
                await self.handle_timeout(motion_id)
            except asyncio.CancelledError:
                pass

        self._timers[motion_id] = asyncio.create_task(timer())
