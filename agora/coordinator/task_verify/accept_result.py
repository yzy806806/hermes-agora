"""Accept-result handler — process TASK_ACCEPT_RESULT from reviewer."""

from __future__ import annotations

import logging
from typing import Any

from ..task_models import TaskStatus

logger = logging.getLogger(__name__)


async def handle_task_accept_result(
    agent_id: str, payload: dict, storage: Any, hub: Any,
) -> None:
    """Process TASK_ACCEPT_RESULT from reviewer agent.

    Updates task status to ACCEPTED or REJECTED.
    If REJECTED: set status back to PENDING for re-assignment.
    """
    task_id = payload.get("task_id")
    accepted = payload.get("accepted", False)
    feedback = payload.get("feedback", "")

    task = await storage.get_task(task_id)
    if task is None:
        logger.warning("accept_result: task %s not found", task_id)
        return

    if accepted:
        await storage.update_task_status(
            task_id, TaskStatus.ACCEPTED.value,
        )
        logger.info("Task %s accepted by %s: %s",
                     task_id, agent_id, feedback)
    else:
        await storage.update_task_status(
            task_id, TaskStatus.REJECTED.value,
            error_message=feedback,
        )
        # Re-queue: REJECTED → PENDING for re-assignment
        await storage.update_task_status(
            task_id, TaskStatus.PENDING.value,
        )
        logger.info("Task %s rejected by %s: %s — re-queued",
                     task_id, agent_id, feedback)
