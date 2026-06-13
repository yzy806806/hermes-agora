"""Tests for NotificationManager (Phase 13.4b)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from agora.coordinator.notifications import NotificationManager
from agora.coordinator.notification_models import (
    Notification, NotificationPriority, NotificationType,
)


def _make_storage() -> AsyncMock:
    """Create a mock storage with create_notification."""
    s = AsyncMock()
    s.create_notification = AsyncMock(return_value={
        "id": "abc123", "type": "pipeline_completed",
        "title": "Done", "body": "b", "project_id": "p1",
        "priority": "medium", "read": False,
    })
    return s


def _make_hub() -> AsyncMock:
    """Create a mock dashboard hub."""
    hub = AsyncMock()
    hub.broadcast_event = AsyncMock(return_value=2)
    return hub


@pytest.mark.asyncio
async def test_create_notification():
    """NotificationManager.create stores and pushes a notification."""
    storage = _make_storage()
    hub = _make_hub()
    mgr = NotificationManager(storage, dashboard_hub=hub)

    notif = await mgr.create(
        type="pipeline_completed", title="Pipeline done",
        body="All tasks passed", project_id="proj1",
    )
    assert isinstance(notif, Notification)
    assert notif.type == NotificationType.PIPELINE_COMPLETED
    assert notif.project_id == "proj1"
    storage.create_notification.assert_awaited_once()
    hub.broadcast_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_without_hub():
    """Without dashboard hub, create still stores but push returns 0."""
    storage = _make_storage()
    mgr = NotificationManager(storage)
    notif = await mgr.create(
        type="agent_offline", title="Agent down",
        body="heartbeat lost", project_id="p2",
    )
    assert notif.type == NotificationType.AGENT_OFFLINE
    storage.create_notification.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_dashboard_hub():
    """set_dashboard_hub injects hub after construction."""
    storage = _make_storage()
    mgr = NotificationManager(storage)
    hub = _make_hub()
    mgr.set_dashboard_hub(hub)
    await mgr.create(
        type="rate_limited", title="Rate limited",
        body="TPM exceeded", project_id="p3",
    )
    hub.broadcast_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_pipeline_completed():
    """Helper creates PIPELINE_COMPLETED with HIGH priority."""
    storage = _make_storage()
    mgr = NotificationManager(storage, dashboard_hub=_make_hub())
    notif = await mgr.notify_pipeline_completed("run1", "proj", "3/3 tasks")
    assert notif.type == NotificationType.PIPELINE_COMPLETED
    assert notif.priority == NotificationPriority.HIGH


@pytest.mark.asyncio
async def test_notify_pipeline_failed():
    """Helper creates PIPELINE_FAILED with CRITICAL priority."""
    storage = _make_storage()
    mgr = NotificationManager(storage, dashboard_hub=_make_hub())
    notif = await mgr.notify_pipeline_failed("run2", "proj", "OOM error")
    assert notif.type == NotificationType.PIPELINE_FAILED
    assert notif.priority == NotificationPriority.CRITICAL


@pytest.mark.asyncio
async def test_notify_review_requested():
    """Helper creates REVIEW_REQUESTED with MEDIUM priority."""
    storage = _make_storage()
    mgr = NotificationManager(storage, dashboard_hub=_make_hub())
    notif = await mgr.notify_review_requested("run3", "proj", ["a.py", "b.py"])
    assert notif.type == NotificationType.REVIEW_REQUESTED
    assert notif.priority == NotificationPriority.MEDIUM


@pytest.mark.asyncio
async def test_notify_agent_offline():
    """Helper creates AGENT_OFFLINE with HIGH priority."""
    storage = _make_storage()
    mgr = NotificationManager(storage, dashboard_hub=_make_hub())
    notif = await mgr.notify_agent_offline("agent-42", "proj")
    assert notif.type == NotificationType.AGENT_OFFLINE
    assert notif.priority == NotificationPriority.HIGH
