"""Quality guard — detects discussion quality issues."""

from __future__ import annotations

import logging

from .quality_guard_checks import run_all_checks
from .quality_guard_models import (
    QualityAlert,
    QualityGuardConfig,
    QualityIssue,
)
from .storage import Storage

logger = logging.getLogger(__name__)

__all__ = [
    "QualityIssue",
    "QualityAlert",
    "QualityGuardConfig",
    "QualityGuard",
]


class QualityGuard:
    """Discussion quality guardian — checks for quality issues."""

    def __init__(
        self, storage: Storage, config: QualityGuardConfig | None = None
    ) -> None:
        self.storage = storage
        self.config = config or QualityGuardConfig()

    async def check_quality(self, motion_id: str) -> list[QualityAlert]:
        """Run all quality checks and return alerts."""
        messages = await self.storage.get_messages(motion_id)
        if not messages:
            return []
        return await run_all_checks(messages, self.config)
