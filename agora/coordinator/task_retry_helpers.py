"""Internal helpers for task retry/failure cascading (Phase 10.1e).

Split from task_retry.py to keep files under 80 lines.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def cascade_block_dependents(
    task_id: str, storage: Any, hub: Any,
) -> list[str]:
    """Block all tasks that depend on the failed task."""
    graph_id = await _get_graph_id(task_id, storage)
    if not graph_id:
        return []
    tasks = await storage.get_tasks_by_graph(graph_id)
    blocked: list[str] = []
    for t in tasks:
        if t["id"] == task_id:
            continue
        deps = t.get("depends_on") or []
        if task_id in deps and t["status"] not in ("done", "accepted", "failed"):
            await storage.update_task_status(
                t["id"], "failed",
                error_message=f"Blocked by failed task {task_id}",
            )
            blocked.append(t["id"])
    return blocked


async def abort_graph(
    task_id: str, storage: Any, hub: Any,
) -> None:
    """Cancel all running/assigned/pending tasks in the graph."""
    graph_id = await _get_graph_id(task_id, storage)
    if not graph_id:
        return
    tasks = await storage.get_tasks_by_graph(graph_id)
    for t in tasks:
        if t["status"] in ("running", "assigned", "pending"):
            await storage.update_task_status(
                t["id"], "failed",
                error_message=f"Graph aborted due to failure of {task_id}",
            )
    await hub.broadcast({
        "type": "GRAPH_ABORTED", "graph_id": graph_id,
        "reason": f"Task {task_id} failed with abort-on-failure enabled",
    })


async def _get_graph_id(task_id: str, storage: Any) -> Optional[str]:
    """Resolve graph_id from a task."""
    task = await storage.get_task(task_id)
    return task.get("graph_id") if task else None
