"""Core LLM-based task graph generation."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

from agora.coordinator.task_models import TaskGraph, TaskNode
from .prompts import TASK_DECOMPOSITION_PROMPT

logger = logging.getLogger(__name__)


async def _llm_generate(
    motion: dict, storage, llm_call, graph_id: str
) -> TaskGraph | None:
    """Use LLM to decompose discussion into task graph.

    Returns None on failure (caller falls back to heuristic).
    """
    motion_id = motion["id"]
    messages = await storage.get_messages(motion["discussion_id"])
    transcript = "\n".join(f"[{m['author']}]: {m['content']}" for m in messages)

    prompt = TASK_DECOMPOSITION_PROMPT.format(
        title=motion.get("title", ""),
        description=motion.get("description", ""),
        decision=motion.get("decision", ""),
        rationale=motion.get("rationale", ""),
        action_items=motion.get("action_items", "[]"),
        transcript=transcript,
    )

    try:
        response = await llm_call(prompt)
        raw_tasks = json.loads(response)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"LLM task generation failed: {e}")
        return None

    if not isinstance(raw_tasks, list):
        logger.warning("LLM returned non-array response")
        return None

    tasks: list[TaskNode] = []
    task_ids: list[str] = []

    for i, item in enumerate(raw_tasks):
        task_id = str(uuid4())
        task_ids.append(task_id)
        depends_on_indices = item.get("depends_on", [])
        depends_on = [task_ids[j] for j in depends_on_indices if j < i]

        tasks.append(TaskNode(
            id=task_id,
            graph_id=graph_id,
            motion_id=motion_id,
            title=item.get("title", f"Task {i+1}"),
            description=item.get("description", ""),
            required_capabilities=item.get("required_capabilities", ["code"]),
            depends_on=depends_on,
        ))

    return TaskGraph(id=graph_id, motion_id=motion_id, tasks=tasks)
