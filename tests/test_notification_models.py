"""Tests for notification models (Phase 13)."""
from datetime import datetime, timezone

from agora.coordinator.notification_models import (
    Notification, NotificationPriority, NotificationType,
)


def test_notification_type_values():
    """All notification types have expected string values."""
    assert NotificationType.PIPELINE_COMPLETED == "pipeline_completed"
    assert NotificationType.PIPELINE_FAILED == "pipeline_failed"
    assert NotificationType.REVIEW_REQUESTED == "review_requested"
    assert NotificationType.AGENT_OFFLINE == "agent_offline"
    assert NotificationType.RATE_LIMITED == "rate_limited"
    assert NotificationType.DISCUSSION_DEADLOCK == "discussion_deadlock"


def test_notification_priority_values():
    """Priority enum has expected levels."""
    assert NotificationPriority.LOW == "low"
    assert NotificationPriority.MEDIUM == "medium"
    assert NotificationPriority.HIGH == "high"
    assert NotificationPriority.CRITICAL == "critical"


def test_notification_model_defaults():
    """Notification model has correct defaults."""
    n = Notification(
        id="abc", type=NotificationType.AGENT_OFFLINE,
        title="Agent down", body="Agent X went offline",
        project_id="proj1",
    )
    assert n.priority == NotificationPriority.MEDIUM
    assert n.read is False
    assert isinstance(n.created_at, datetime)


def test_notification_model_custom_priority():
    """Notification can be created with custom priority."""
    n = Notification(
        id="xyz", type=NotificationType.PIPELINE_FAILED,
        title="Pipeline failed", body="Error in phase X",
        project_id="proj2", priority=NotificationPriority.CRITICAL,
    )
    assert n.priority == NotificationPriority.CRITICAL
