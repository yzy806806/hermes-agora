"""Legacy sync resource tracker helpers — backward compat mixin."""

from __future__ import annotations

from .task_models import ResourceLock, TaskNode


class FileResourceTrackerLegacyMixin:
    """Mixin providing legacy sync API methods for FileResourceTracker."""

    def acquire_sync(
        self, task_id: str, paths: list[str], mode: str = "write",
    ) -> bool:
        """Sync: try to acquire locks on multiple paths."""
        for path in paths:
            existing = self._locks.get(path)
            if existing and existing.locked_by != task_id:
                if mode == "write" or existing.lock_type == "write":
                    return False
        for path in paths:
            existing = self._locks.get(path)
            if existing and existing.locked_by == task_id:
                continue
            self._locks[path] = ResourceLock(
                resource_path=path, locked_by=task_id, lock_type=mode)
        return True

    def release_all(self, task_id: str) -> list[str]:
        """Release all locks held by a task. Returns unblocked task ids."""
        waiting: list[str] = []
        for path, lock in list(self._locks.items()):
            if lock.locked_by == task_id:
                waiting.extend(lock.waiting_tasks)
                del self._locks[path]
        return list(set(waiting))

    def check_conflict(self, task_a: TaskNode, task_b: TaskNode) -> bool:
        return bool(set(task_a.artifact_paths) & set(task_b.artifact_paths))

    def get_locked_paths(self, task_id: str) -> list[str]:
        return [p for p, lk in self._locks.items() if lk.locked_by == task_id]

    def get_held_locks(self, task_id: str) -> list[str]:
        return self.get_locked_paths(task_id)

    def add_waiting(self, path: str, task_id: str) -> None:
        lock = self._locks.get(path)
        if lock and task_id not in lock.waiting_tasks:
            lock.waiting_tasks.append(task_id)

    def add_waiter(self, task_id: str, path: str) -> None:
        self.add_waiting(path, task_id)