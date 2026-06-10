"""File Resource Tracker — async resource conflict detection (Phase 10.1c)."""

from __future__ import annotations

import asyncio
import logging

from .task_models import ConflictReport, ResourceLock, TaskNode
from .task_resource_compat import FileResourceTrackerLegacyMixin
from .task_resource_detect import detect_conflicts

logger = logging.getLogger(__name__)


class FileResourceTracker(FileResourceTrackerLegacyMixin):
    """Detects when parallel tasks conflict on filesystem resources.
    read-read sharing OK; read-write and write-write are conflicts."""

    def __init__(self) -> None:
        self._locks: dict[str, ResourceLock] = {}
        self._wait_events: dict[str, asyncio.Event] = {}

    async def acquire(
        self, task_id: str, resource_path: str | list[str],
        lock_type: str = "write",
    ) -> bool:
        """Async: acquire lock on one path or list. Returns True if granted."""
        if isinstance(resource_path, list):
            return self.acquire_sync(task_id, resource_path, lock_type)
        existing = self._locks.get(resource_path)
        if existing is None:
            self._locks[resource_path] = ResourceLock(
                resource_path=resource_path,
                locked_by=task_id, lock_type=lock_type)
            return True
        if existing.locked_by == task_id:
            return True
        if existing.lock_type == "read" and lock_type == "read":
            return True
        if task_id not in existing.waiting_tasks:
            existing.waiting_tasks.append(task_id)
        logger.info("Task %s waiting for %s", task_id, resource_path)
        return False

    async def release(
        self, task_id: str, resource_path: str | None = None,
    ) -> list[str]:
        """Async: release one lock or all. Returns unblocked task ids."""
        if resource_path is None:
            return self.release_all(task_id)
        lock = self._locks.get(resource_path)
        if lock is None or lock.locked_by != task_id:
            return []
        if lock.waiting_tasks:
            next_task = lock.waiting_tasks.pop(0)
            lock.locked_by = next_task
            lock.lock_type = "write"
            event = self._wait_events.get(next_task)
            if event:
                event.set()
            return [next_task]
        del self._locks[resource_path]
        return []

    def detect_conflicts(self, tasks: list[TaskNode]) -> list:
        return detect_conflicts(tasks)