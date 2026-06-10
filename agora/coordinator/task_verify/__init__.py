"""Task Verification — auto-verify simple tasks, delegate complex review.

Public API:
- verify_task(task_id, storage, hub) — main entry point
- is_simple_task(task, storage) — check if auto-acceptable (async)
- auto_verify(task) — file existence checks
- delegate_review(task, storage, hub) — send to reviewer
- handle_task_accept_result(agent_id, payload, storage, hub)
"""

from __future__ import annotations

import logging
from typing import Any

from .auto_check import auto_verify
from .delegate import delegate_review
from .accept_result import handle_task_accept_result
from .simple_check import is_simple_task
from ..task_models import TaskStatus

logger = logging.getLogger(__name__)


async def verify_task(
    task_id: str, storage: Any, hub: Any,
) -> None:
    """Verify a completed task.

    Decision tree:
    1. Fetch task from storage
    2. Run auto-checks (artifact existence)
    3. If auto-checks pass AND task is simple → auto-accept
    4. Else → delegate to reviewer via TASK_VERIFY WS message
    """
    task = await storage.get_task(task_id)
    if task is None:
        logger.warning("verify_task: task %s not found", task_id)
        return
    if task["status"] != TaskStatus.DONE.value:
        logger.warning("verify_task: task %s not DONE (status=%s)",
                       task_id, task["status"])
        return

    passed, reason = await auto_verify(task)
    if passed and await is_simple_task(task, storage):
        await storage.update_task_status(
            task_id, TaskStatus.ACCEPTED.value,
        )
        logger.info("Auto-accepted task %s: %s", task_id, reason)
        return

    await delegate_review(task, storage, hub)
