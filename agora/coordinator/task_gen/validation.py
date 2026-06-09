"""DAG validation for task graphs.

Checks: no self-dependency, all depends_on IDs exist, no cycles.
"""

from __future__ import annotations

from agora.coordinator.task_models import TaskNode


def _validate_graph(tasks: list[TaskNode]) -> None:
    """Validate DAG integrity. Raises ValueError on invalid graph."""
    task_ids = {t.id for t in tasks}

    for task in tasks:
        if task.id in task.depends_on:
            raise ValueError(f"Task {task.id} depends on itself")

        for dep_id in task.depends_on:
            if dep_id not in task_ids:
                raise ValueError(
                    f"Task {task.id} depends on unknown task {dep_id}"
                )

    visited, rec_stack = set(), set()

    def has_cycle(task_id: str) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)
        task = next(t for t in tasks if t.id == task_id)
        for dep_id in task.depends_on:
            if dep_id not in visited:
                if has_cycle(dep_id):
                    return True
            elif dep_id in rec_stack:
                return True
        rec_stack.remove(task_id)
        return False

    for task in tasks:
        if task.id not in visited:
            if has_cycle(task.id):
                raise ValueError("Task graph contains a cycle")
