"""Test TASK_* MessageType enum values (Phase 9.2d-1)."""

from agora.coordinator.models import MessageType


def test_task_message_types_exist():
    """All 6 Phase 9 TASK_* enum values must be present."""
    expected = [
        "TASK_ASSIGNED",
        "TASK_STATUS",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "TASK_VERIFY",
        "TASK_ACCEPT_RESULT",
    ]
    for name in expected:
        assert hasattr(MessageType, name), f"Missing {name}"


def test_task_message_type_values():
    """Enum values must match their string names."""
    assert MessageType.TASK_ASSIGNED.value == "TASK_ASSIGNED"
    assert MessageType.TASK_STATUS.value == "TASK_STATUS"
    assert MessageType.TASK_COMPLETED.value == "TASK_COMPLETED"
    assert MessageType.TASK_FAILED.value == "TASK_FAILED"
    assert MessageType.TASK_VERIFY.value == "TASK_VERIFY"
    assert MessageType.TASK_ACCEPT_RESULT.value == "TASK_ACCEPT_RESULT"


def test_existing_message_types_unchanged():
    """Pre-existing enum values must not be affected."""
    assert MessageType.REGISTER.value == "REGISTER"
    assert MessageType.SPEAK.value == "SPEAK"
    assert MessageType.VOTE.value == "VOTE"
    assert MessageType.DEVILS_ADVOCATE_RESPONSE.value == (
        "DEVILS_ADVOCATE_RESPONSE"
    )
