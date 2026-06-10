"""Batch conflict detection for task artifact paths (Phase 10.1c)."""

from __future__ import annotations

from .task_models import ConflictReport, TaskNode


def detect_conflicts(tasks: list[TaskNode]) -> list[ConflictReport]:
    """Check all tasks for resource conflicts based on artifact_paths.

    Convention: paths prefixed with "r:" indicate read access;
    unprefixed paths default to write access.
    Read-read sharing is allowed; read-write and write-write are conflicts.
    """
    conflicts: list[ConflictReport] = []
    path_map: dict[str, list[tuple[str, str]]] = {}
    for task in tasks:
        for path in task.artifact_paths:
            if path.startswith("r:"):
                mode, clean = "read", path[2:]
            else:
                mode, clean = "write", path
            path_map.setdefault(clean, []).append((task.id, mode))
    for path, entries in path_map.items():
        if len(entries) < 2:
            continue
        for i, (tid_a, mode_a) in enumerate(entries):
            for tid_b, mode_b in entries[i + 1:]:
                if mode_a == "read" and mode_b == "read":
                    continue
                ctype = "read-write" if "read" in (mode_a, mode_b) else "write-write"
                conflicts.append(ConflictReport(
                    task_a=tid_a, task_b=tid_b,
                    resource_path=path, conflict_type=ctype,
                ))
    return conflicts
