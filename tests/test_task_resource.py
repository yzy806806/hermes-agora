"""Tests for FileResourceTracker — resource conflict detection."""

import pytest
from agora.coordinator.task_resource import FileResourceTracker
from agora.coordinator.task_models import TaskNode


def _make_task(tid, paths, graph_id="g1", motion_id="m1"):
    return TaskNode(
        id=tid, graph_id=graph_id, motion_id=motion_id,
        title=f"Task {tid}", artifact_paths=paths,
    )


# --- async acquire / release ---

@pytest.mark.asyncio
async def test_acquire_write_granted():
    tracker = FileResourceTracker()
    ok = await tracker.acquire("t1", "src/main.py", "write")
    assert ok is True
    assert "src/main.py" in tracker._locks


@pytest.mark.asyncio
async def test_acquire_read_read_shared():
    tracker = FileResourceTracker()
    ok1 = await tracker.acquire("t1", "src/main.py", "read")
    ok2 = await tracker.acquire("t2", "src/main.py", "read")
    assert ok1 is True
    assert ok2 is True


@pytest.mark.asyncio
async def test_acquire_write_blocked_by_write():
    tracker = FileResourceTracker()
    ok1 = await tracker.acquire("t1", "src/main.py", "write")
    ok2 = await tracker.acquire("t2", "src/main.py", "write")
    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_acquire_read_blocked_by_write():
    tracker = FileResourceTracker()
    ok1 = await tracker.acquire("t1", "src/main.py", "write")
    ok2 = await tracker.acquire("t2", "src/main.py", "read")
    assert ok1 is True
    assert ok2 is False


@pytest.mark.asyncio
async def test_acquire_write_blocked_by_read():
    tracker = FileResourceTracker()
    ok1 = await tracker.acquire("t1", "src/main.py", "read")
    ok2 = await tracker.acquire("t2", "src/main.py", "write")
    assert ok1 is True
    assert ok2 is False


# --- async release ---

@pytest.mark.asyncio
async def test_release_removes_lock():
    tracker = FileResourceTracker()
    await tracker.acquire("t1", "src/main.py", "write")
    await tracker.release("t1", "src/main.py")
    assert "src/main.py" not in tracker._locks


@pytest.mark.asyncio
async def test_release_wakes_waiter():
    tracker = FileResourceTracker()
    await tracker.acquire("t1", "src/main.py", "write")
    await tracker.acquire("t2", "src/main.py", "write")
    await tracker.release("t1", "src/main.py")
    lock = tracker._locks["src/main.py"]
    assert lock.locked_by == "t2"


# --- detect_conflicts ---

def test_detect_no_conflict():
    tracker = FileResourceTracker()
    tasks = [_make_task("t1", ["a.py"]), _make_task("t2", ["b.py"])]
    assert tracker.detect_conflicts(tasks) == []


def test_detect_write_write_conflict():
    tracker = FileResourceTracker()
    tasks = [_make_task("t1", ["a.py"]), _make_task("t2", ["a.py"])]
    conflicts = tracker.detect_conflicts(tasks)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "write-write"


def test_detect_read_write_conflict():
    tracker = FileResourceTracker()
    tasks = [_make_task("t1", ["r:a.py"]), _make_task("t2", ["a.py"])]
    conflicts = tracker.detect_conflicts(tasks)
    assert len(conflicts) == 1
    assert conflicts[0].conflict_type == "read-write"


def test_detect_read_read_no_conflict():
    tracker = FileResourceTracker()
    tasks = [_make_task("t1", ["r:a.py"]), _make_task("t2", ["r:a.py"])]
    assert tracker.detect_conflicts(tasks) == []


def test_detect_multiple_paths():
    tracker = FileResourceTracker()
    tasks = [_make_task("t1", ["a.py", "b.py"]), _make_task("t2", ["a.py", "c.py"])]
    conflicts = tracker.detect_conflicts(tasks)
    assert len(conflicts) == 1
    assert conflicts[0].resource_path == "a.py"
