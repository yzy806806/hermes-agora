"""Heuristic fallback for task graph generation.

Used when LLM call fails or returns unparseable output.
Creates one task per action_item with sequential dependencies.
"""

from __future__ import annotations

import json
from uuid import uuid4

from agora.coordinator.task_models import TaskGraph, TaskNode


def heuristic_generate(motion: dict) -> TaskGraph:
    """Generate a simple task graph: one task per action_item, chained.

    Each task gets required_capabilities=["code"] by default.
    Tasks are sequential: task_N depends_on task_N-1.
    """
    motion_id = motion["id"]
    graph_id = str(uuid4())

    raw_items = motion.get("action_items", "[]")
    if isinstance(raw_items, str):
        items = json.loads(raw_items)
    else:
        items = raw_items

    tasks: list[TaskNode] = []
    prev_id: str | None = None

    for item in items:
        task_id = str(uuid4())
        title = item if isinstance(item, str) else item.get("title", str(item))
        desc = "" if isinstance(item, str) else item.get("description", "")
        depends_on = [prev_id] if prev_id else []

        tasks.append(TaskNode(
            id=task_id,
            graph_id=graph_id,
            motion_id=motion_id,
            title=title,
            description=desc,
            required_capabilities=["code"],
            depends_on=depends_on,
        ))
        prev_id = task_id

    return TaskGraph(id=graph_id, motion_id=motion_id, tasks=tasks)
