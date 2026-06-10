"""Parallel execution event handlers (Phase 10)."""

from __future__ import annotations

import logging
from typing import Any

from .task_models import TaskNode, TaskStatus
from .task_parallel_helpers import priority_value, release_resources

logger = logging.getLogger(__name__)


async def on_task_complete(
    task_id: str, graph_tasks: dict[str, TaskNode],
    completed: set[str], failed: set[str], result: dict,
    agent_slots: dict[str, int], resource_tracker: Any,
    runqueue: Any,
) -> None:
    """Handle task completion — release resources, unblock dependents."""
    completed.add(task_id)
    result["completed"].append(task_id)
    task = graph_tasks.get(task_id)
    if task and task.assigned_to:
        agent_slots[task.assigned_to] = agent_slots.get(task.assigned_to, 0) + 1
    await release_resources(task_id, resource_tracker)
    # Re-evaluate dependents
    for tid, t in graph_tasks.items():
        if tid not in completed and tid not in failed:
            if t.status == TaskStatus.PENDING and _deps_met(t, completed):
                await runqueue.put((priority_value(t), tid))


async def on_task_failed(
    task_id: str, error: str, graph_tasks: dict[str, TaskNode],
    failed: set[str], result: dict, agent_slots: dict[str, int],
    resource_tracker: Any,
) -> None:
    """Handle task failure — cascade to dependents."""
    failed.add(task_id)
    result["failed"].append({"task_id": task_id, "error": error})
    task = graph_tasks.get(task_id)
    if task and task.assigned_to:
        agent_slots[task.assigned_to] = agent_slots.get(task.assigned_to, 0) + 1
    await release_resources(task_id, resource_tracker)
    # Cascade failure to all dependents
    for tid, t in graph_tasks.items():
        if task_id in t.depends_on and tid not in failed:
            failed.add(tid)
            result["failed"].append(
                {"task_id": tid, "error": f"dep {task_id} failed"})


def _deps_met(task: TaskNode, completed: set[str]) -> bool:
    return all(d in completed for d in task.depends_on)
