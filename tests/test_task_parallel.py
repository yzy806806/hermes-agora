"""Tests for Phase 10 parallel execution modules."""

import asyncio
import pytest

from agora.coordinator.task_models import (
    ConflictReport, ExecutionSlot, ResourceLock,
    TaskGraph, TaskNode, TaskStatus,
)
from agora.coordinator.task_resource import FileResourceTracker


# -- Model tests --

class TestExecutionSlot:
    def test_defaults(self):
        slot = ExecutionSlot(task_id="t1", agent_id="a1")
        assert slot.status == "running"
        assert slot.started_at is not None

    def test_completing(self):
        slot = ExecutionSlot(task_id="t1", agent_id="a1", status="completing")
        assert slot.status == "completing"


class TestResourceLock:
    def test_defaults(self):
        lock = ResourceLock(resource_path="src/main.py", locked_by="t1")
        assert lock.lock_type == "write"
        assert lock.waiting_tasks == []


class TestConflictReport:
    def test_defaults(self):
        cr = ConflictReport(task_a="t1", task_b="t2", resource_path="x.py")
        assert cr.conflict_type == "write-write"


class TestTaskGraphPhase10:
    def test_parallel_defaults(self):
        g = TaskGraph(id="g1", motion_id="m1")
        assert g.parallel_mode == "auto"
        assert g.max_parallel_slots == 10
        assert g.resource_conflict_policy == "warn"


# -- Resource tracker tests --

class TestFileResourceTracker:
    @pytest.mark.asyncio
    async def test_acquire_single_path(self):
        tracker = FileResourceTracker()
        ok = await tracker.acquire("t1", "src/a.py")
        assert ok is True

    @pytest.mark.asyncio
    async def test_acquire_conflict(self):
        tracker = FileResourceTracker()
        await tracker.acquire("t1", "src/a.py")
        ok = await tracker.acquire("t2", "src/a.py")
        assert ok is False

    @pytest.mark.asyncio
    async def test_acquire_list_sync(self):
        tracker = FileResourceTracker()
        ok = await tracker.acquire("t1", ["src/a.py", "src/b.py"])
        assert ok is True

    @pytest.mark.asyncio
    async def test_acquire_list_conflict(self):
        tracker = FileResourceTracker()
        await tracker.acquire("t1", ["src/a.py"])
        ok = await tracker.acquire("t2", ["src/a.py", "src/b.py"])
        assert ok is False

    @pytest.mark.asyncio
    async def test_read_read_sharing(self):
        tracker = FileResourceTracker()
        await tracker.acquire("t1", "src/a.py", "read")
        ok = await tracker.acquire("t2", "src/a.py", "read")
        assert ok is True

    @pytest.mark.asyncio
    async def test_release_transfers_lock(self):
        tracker = FileResourceTracker()
        await tracker.acquire("t1", "src/a.py")
        await tracker.acquire("t2", "src/a.py")  # blocked, added as waiter
        unblocked = await tracker.release("t1", "src/a.py")
        assert "t2" in unblocked

    @pytest.mark.asyncio
    async def test_release_all(self):
        tracker = FileResourceTracker()
        await tracker.acquire("t1", "src/a.py")
        await tracker.acquire("t1", "src/b.py")
        unblocked = await tracker.release("t1")
        assert tracker.get_locked_paths("t1") == []

    @pytest.mark.asyncio
    async def test_detect_conflicts(self):
        ta = TaskNode(id="t1", graph_id="g1", motion_id="m1",
                       title="A", artifact_paths=["src/x.py"])
        tb = TaskNode(id="t2", graph_id="g1", motion_id="m1",
                       title="B", artifact_paths=["src/x.py"])
        tracker = FileResourceTracker()
        conflicts = tracker.detect_conflicts([ta, tb])
        assert len(conflicts) == 1

    @pytest.mark.asyncio
    async def test_no_conflict_different_paths(self):
        ta = TaskNode(id="t1", graph_id="g1", motion_id="m1",
                       title="A", artifact_paths=["src/a.py"])
        tb = TaskNode(id="t2", graph_id="g1", motion_id="m1",
                       title="B", artifact_paths=["src/b.py"])
        tracker = FileResourceTracker()
        assert len(tracker.detect_conflicts([ta, tb])) == 0
