"""Tests for notification REST API (Phase 13.4c)."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agora.coordinator.main import create_app
from agora.coordinator.notification_router import (
    init_notification_router_deps,
)
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def notif_client(tmp_path):
    """Create a test client with notification routes wired."""
    db_path = str(tmp_path / "notif_api.db")
    storage = Storage(db_path)
    await storage.init_db()
    init_notification_router_deps(storage)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client, storage


@pytest.mark.asyncio
async def test_list_notifications_empty(notif_client):
    client, _ = notif_client
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["unread_count"] == 0
    assert data["notifications"] == []


@pytest.mark.asyncio
async def test_list_notifications_with_data(notif_client):
    client, storage = notif_client
    await storage.create_notification(
        type="pipeline_completed", title="Done",
        body="Pipeline finished", project_id="p1")
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["unread_count"] >= 1
    assert data["notifications"][0]["type"] == "pipeline_completed"


@pytest.mark.asyncio
async def test_filter_by_project(notif_client):
    client, storage = notif_client
    await storage.create_notification(
        type="agent_offline", title="A", body="b", project_id="pa")
    await storage.create_notification(
        type="rate_limited", title="R", body="b", project_id="pb")
    resp = await client.get(
        "/api/v1/notifications", params={"project_id": "pa"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(n["project_id"] == "pa" for n in data["notifications"])


@pytest.mark.asyncio
async def test_filter_unread_only(notif_client):
    client, storage = notif_client
    n = await storage.create_notification(
        type="pipeline_failed", title="F", body="b", project_id="pu")
    await storage.mark_notification_read(n["id"])
    await storage.create_notification(
        type="discussion_deadlock", title="D", body="b", project_id="pu")
    resp = await client.get(
        "/api/v1/notifications",
        params={"project_id": "pu", "unread_only": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 1
    assert data["notifications"][0]["title"] == "D"


@pytest.mark.asyncio
async def test_filter_by_priority(notif_client):
    client, storage = notif_client
    await storage.create_notification(
        type="pipeline_failed", title="Crit", body="b",
        project_id="pp", priority="critical")
    await storage.create_notification(
        type="review_requested", title="Med", body="b",
        project_id="pp", priority="medium")
    resp = await client.get(
        "/api/v1/notifications",
        params={"project_id": "pp", "priority": "critical"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(n["priority"] == "critical" for n in data["notifications"])


@pytest.mark.asyncio
async def test_mark_notification_read(notif_client):
    client, storage = notif_client
    n = await storage.create_notification(
        type="review_requested", title="R", body="b", project_id="pr")
    resp = await client.post(
        f"/api/v1/notifications/{n['id']}/read")
    assert resp.status_code == 200
    assert resp.json()["read"] is True


@pytest.mark.asyncio
async def test_mark_read_not_found(notif_client):
    client, _ = notif_client
    resp = await client.post(
        "/api/v1/notifications/nonexistent/read")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_all_read(notif_client):
    client, storage = notif_client
    await storage.create_notification(
        type="agent_offline", title="A", body="b", project_id="pm")
    await storage.create_notification(
        type="rate_limited", title="B", body="b", project_id="pm")
    resp = await client.post(
        "/api/v1/notifications/read-all",
        json={"project_id": "pm"},
    )
    assert resp.status_code == 200
    assert resp.json()["marked_count"] >= 2
