"""Tests for notification storage CRUD (Phase 13)."""
import pytest
from agora.coordinator.storage import Storage


@pytest.mark.asyncio
async def test_create_notification(storage: Storage):
    """Create a notification and verify fields."""
    n = await storage.create_notification(
        type="pipeline_completed", title="Done",
        body="Pipeline X finished", project_id="proj1")
    assert n["id"] is not None
    assert n["type"] == "pipeline_completed"
    assert n["title"] == "Done"
    assert n["project_id"] == "proj1"
    assert n["priority"] == "medium"
    assert n["read"] is False


@pytest.mark.asyncio
async def test_get_notification(storage: Storage):
    """Get a notification by ID."""
    created = await storage.create_notification(
        type="agent_offline", title="Offline",
        body="Agent down", project_id="p1")
    fetched = await storage.get_notification(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]


@pytest.mark.asyncio
async def test_get_notification_not_found(storage: Storage):
    """Getting a non-existent notification returns None."""
    assert await storage.get_notification("nope") is None


@pytest.mark.asyncio
async def test_list_notifications_filter_project(storage: Storage):
    """List notifications filtered by project_id."""
    await storage.create_notification(
        type="rate_limited", title="R1", body="b", project_id="pa")
    await storage.create_notification(
        type="review_requested", title="R2", body="b", project_id="pb")
    await storage.create_notification(
        type="agent_offline", title="R3", body="b", project_id="pa")
    pa = await storage.list_notifications(project_id="pa")
    assert len(pa) == 2
    all_n = await storage.list_notifications()
    assert len(all_n) >= 3


@pytest.mark.asyncio
async def test_list_notifications_unread_only(storage: Storage):
    """List only unread notifications."""
    n1 = await storage.create_notification(
        type="pipeline_failed", title="F1", body="b", project_id="pu")
    await storage.mark_notification_read(n1["id"])
    await storage.create_notification(
        type="discussion_deadlock", title="D1", body="b", project_id="pu")
    unread = await storage.list_notifications(
        project_id="pu", unread_only=True)
    assert len(unread) == 1
    assert unread[0]["title"] == "D1"


@pytest.mark.asyncio
async def test_mark_read(storage: Storage):
    """Mark a single notification as read."""
    n = await storage.create_notification(
        type="pipeline_completed", title="T", body="b", project_id="pr")
    assert n["read"] is False
    updated = await storage.mark_notification_read(n["id"])
    assert updated is not None
    assert updated["read"] is True


@pytest.mark.asyncio
async def test_mark_all_read(storage: Storage):
    """Mark all notifications as read."""
    await storage.create_notification(
        type="agent_offline", title="A", body="b", project_id="pm")
    await storage.create_notification(
        type="rate_limited", title="B", body="b", project_id="pm")
    count = await storage.mark_all_notifications_read(project_id="pm")
    assert count == 2
    unread = await storage.list_notifications(
        project_id="pm", unread_only=True)
    assert len(unread) == 0
