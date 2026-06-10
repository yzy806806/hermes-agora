"""Parallel execution WebSocket message helpers.

Coordinator → Agent messages for parallel task execution (Phase 10).
These are outbound messages sent by the coordinator to agents.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import MessageType

logger = logging.getLogger(__name__)


async def send_task_blocked(
    hub: Any, agent_id: str, task_id: str,
    reason: str, waiting_for: list[str] | None = None,
) -> None:
    """Send TASK_BLOCKED to an agent (resource conflict)."""
    await hub.send(agent_id, {
        "type": MessageType.TASK_BLOCKED.value,
        "payload": {
            "task_id": task_id,
            "reason": reason,
            "waiting_for": waiting_for or [],
        },
    })
    logger.info("Task %s blocked for agent %s: %s", task_id, agent_id, reason)


async def send_task_unblocked(
    hub: Any, agent_id: str, task_id: str,
) -> None:
    """Send TASK_UNBLOCKED to an agent (resource available)."""
    await hub.send(agent_id, {
        "type": MessageType.TASK_UNBLOCKED.value,
        "payload": {"task_id": task_id},
    })
    logger.info("Task %s unblocked for agent %s", task_id, agent_id)


async def send_task_retry(
    hub: Any, agent_id: str, task_id: str,
    reason: str, max_attempts: int = 3,
) -> None:
    """Send TASK_RETRY to an agent (coordinator requests retry)."""
    await hub.send(agent_id, {
        "type": MessageType.TASK_RETRY.value,
        "payload": {
            "task_id": task_id,
            "reason": reason,
            "max_attempts": max_attempts,
        },
    })
    logger.info("Task %s retry requested for agent %s", task_id, agent_id)


async def broadcast_graph_complete(
    hub: Any, graph_id: str, summary: dict[str, Any],
) -> None:
    """Broadcast GRAPH_COMPLETE to all connected agents."""
    await hub.broadcast({
        "type": MessageType.GRAPH_COMPLETE.value,
        "payload": {
            "graph_id": graph_id,
            "summary": summary,
        },
    })
    logger.info("Graph %s complete: %s", graph_id, summary)
