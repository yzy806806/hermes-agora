"""Tests for Phase 10 parallel execution MessageType values."""

from agora.coordinator.models import MessageType


def test_phase10_message_types_exist():
    """All Phase 10 parallel execution enum values must be present."""
    expected = [
        "TASK_STARTED", "TASK_BLOCKED", "TASK_UNBLOCKED",
        "TASK_RETRY", "TASK_PROGRESS", "GRAPH_COMPLETE",
        "GRAPH_ABORTED",
    ]
    for name in expected:
        assert hasattr(MessageType, name), f"Missing {name}"


def test_phase10_message_type_values():
    """Enum values must match their string names."""
    assert MessageType.TASK_STARTED.value == "TASK_STARTED"
    assert MessageType.TASK_BLOCKED.value == "TASK_BLOCKED"
    assert MessageType.TASK_UNBLOCKED.value == "TASK_UNBLOCKED"
    assert MessageType.TASK_RETRY.value == "TASK_RETRY"
    assert MessageType.TASK_PROGRESS.value == "TASK_PROGRESS"
    assert MessageType.GRAPH_COMPLETE.value == "GRAPH_COMPLETE"


def test_phase9_message_types_unchanged():
    """Pre-existing Phase 9 enum values must not be affected."""
    assert MessageType.TASK_ASSIGNED.value == "TASK_ASSIGNED"
    assert MessageType.TASK_STATUS.value == "TASK_STATUS"
    assert MessageType.TASK_COMPLETED.value == "TASK_COMPLETED"
    assert MessageType.TASK_FAILED.value == "TASK_FAILED"
    assert MessageType.HEARTBEAT.value == "HEARTBEAT"
