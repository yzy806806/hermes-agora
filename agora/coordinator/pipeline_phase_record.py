"""Pipeline session recording phase (Phase 13)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agora.coordinator.pipeline_models import PipelinePhase, PipelineRun

logger = logging.getLogger(__name__)


async def record_pipeline_session(
    storage: Any, run: PipelineRun,
) -> None:
    """Phase: COMPLETED — persist the pipeline run as a session record.

    Updates the run's phase to COMPLETED and sets completed_at.
    """
    try:
        run.phase = PipelinePhase.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Pipeline %s completed: %d/%d tasks, version=%s",
            run.id, run.tasks_completed, run.tasks_total,
            run.release_version,
        )
    except Exception as exc:
        logger.error("Failed to record pipeline session: %s", exc)
