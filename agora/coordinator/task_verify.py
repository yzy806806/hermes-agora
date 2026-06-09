"""Task Verification — auto-verify simple tasks, delegate complex review."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .task_models import TaskStatus

logger = logging.getLogger(__name__)

# Round-robin index for reviewer selection
_rr_index = [0]

# Capabilities considered safe for auto-accept
_SAFE_CAPS = {"docs", "code"}


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

    passed, reason = await _auto_verify(task)
    if passed and _is_simple_task(task, storage):
        await storage.update_task_status(
            task_id, TaskStatus.ACCEPTED.value,
        )
        logger.info("Auto-accepted task %s: %s", task_id, reason)
        return

    await _delegate_review(task, storage, hub)


async def _auto_verify(task: dict) -> tuple[bool, str]:
    """Run automated verification checks (Phase 9: file existence only).

    Returns (passed, reason).
    """
    artifact_paths = task.get("artifact_paths") or []

    missing = [p for p in artifact_paths if not os.path.exists(p)]
    if missing:
        return False, f"Missing artifacts: {', '.join(missing)}"

    if not artifact_paths:
        return True, "No artifacts declared; auto-accepting"

    return True, "All artifacts present"


def _is_simple_task(task: dict, storage: Any = None) -> bool:
    """Determine if a task is simple enough for auto-accept.

    Simple: single artifact, no deps or all deps accepted,
    capabilities only docs or code (not security/deploy).
    """
    artifact_paths = task.get("artifact_paths") or []
    if len(artifact_paths) > 1:
        return False

    caps = task.get("required_capabilities") or []
    if isinstance(caps, str):
        caps = json.loads(caps)
    if not caps:
        return False
    if not set(caps) <= _SAFE_CAPS:
        return False

    return True


async def _delegate_review(
    task: dict, storage: Any, hub: Any,
) -> None:
    """Send TASK_VERIFY to a reviewer agent.

    Find online agents with 'review' capability, pick one round-robin.
    If no reviewer available, leave task DONE and log warning.
    """
    online_ids = set(hub.get_online_agents())
    all_agents = await storage.list_agents(online_only=False)

    reviewers: list[dict] = []
    for agent in all_agents:
        aid = agent["agent_id"]
        if aid not in online_ids:
            continue
        caps = agent.get("capabilities") or []
        if isinstance(caps, str):
            caps = json.loads(caps)
        if "review" in caps:
            reviewers.append(agent)

    if not reviewers:
        logger.warning(
            "No reviewer available for task %s; leaving DONE",
            task["id"],
        )
        return

    n = len(reviewers)
    idx = _rr_index[0] % n
    _rr_index[0] += 1
    reviewer = reviewers[idx]
    reviewer_id = reviewer["agent_id"]

    msg = {
        "type": "TASK_VERIFY",
        "motion_id": task.get("motion_id"),
        "payload": {
            "task_id": task["id"],
            "title": task.get("title", ""),
            "assigned_to": task.get("assigned_to"),
            "artifact_paths": task.get("artifact_paths", []),
            "description": task.get("description", ""),
        },
    }
    sent = await hub.send(reviewer_id, msg)
    if sent:
        logger.info("Delegated review of task %s to %s",
                     task["id"], reviewer_id)
    else:
        logger.warning("Failed to send TASK_VERIFY to %s", reviewer_id)


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
