"""Task Execution — state machine and WebSocket message handlers."""

from __future__ import annotations

import logging
from typing import Any

from .models import MessageType

logger = logging.getLogger(__name__)

# Valid state transitions: current -> set of allowed next states
VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"assigned"},
    "assigned": {"running", "failed"},
    "running": {"done", "failed"},
    "done": {"accepted", "rejected"},
    "rejected": {"pending"},
    "failed": set(),   # terminal
    "accepted": set(), # terminal
}


def _is_valid_transition(current: str, next_status: str) -> bool:
    """Check if a state transition is allowed."""
    return next_status in VALID_TRANSITIONS.get(current, set())


async def _send_error(
    hub: Any, agent_id: str, code: str, message: str,
) -> None:
    """Send an ERROR message back to the agent."""
    await hub.send(agent_id, {
        "type": MessageType.ERROR.value,
        "payload": {"code": code, "message": message},
    })


async def handle_task_status(
    agent_id: str,
    payload: dict,
    storage: Any,
    hub: Any,
) -> None:
    """Process TASK_STATUS from an agent.

    Validates the transition, updates DB, and triggers next steps:
    - RUNNING -> DONE: trigger verification
    - -> FAILED: log error event
    """
    task_id = payload.get("task_id")
    new_status = payload.get("status") or ""
    if not new_status:
        await _send_error(hub, agent_id, "missing_status",
                          "Missing status in payload")
        return
    task = await storage.get_task(task_id)
    if not task:
        await _send_error(hub, agent_id, "task_not_found",
                          f"Task {task_id} not found")
        return
    if not _is_valid_transition(task["status"], new_status):
        await _send_error(hub, agent_id, "invalid_transition",
                          f"Cannot go from {task['status']} to {new_status}")
        return
    await storage.update_task_status(
        task_id, new_status,
        error_message=payload.get("error"),
        artifact_paths=payload.get("artifact_paths"),
    )
    if new_status == "done":
        from .task_verify import verify_task
        await verify_task(task_id, storage, hub)
    if new_status == "failed":
        await storage.log_event(
            "task.failed",
            f"Task {task_id} failed: {payload.get('error', '')}",
            motion_id=task["motion_id"],
            agent_id=agent_id,
        )
