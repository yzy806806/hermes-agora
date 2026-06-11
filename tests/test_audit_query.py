"""Tests for audit query REST API endpoint (Phase 11.1d)."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from agora.coordinator.audit import AuditEvent, AuditEventType, AuditLogger
from agora.coordinator.dashboard import init_audit_deps, init_dashboard_deps
from agora.coordinator.main import create_app
from agora.coordinator.router import init_deps
from agora.coordinator.state import StateMachine
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def audit_logger(tmp_path):
    db_path = str(tmp_path / "test_audit.db")
    s = Storage(db_path)
    await s.init_db()
    al = AuditLogger(db_path)
    yield al


@pytest_asyncio.fixture(loop_scope="session")
async def client(tmp_path, audit_logger):
    app = create_app()
    db_path = str(tmp_path / "test_audit.db")
    storage = Storage(db_path)
    await storage.init_db()
    sm = StateMachine(storage)
    init_deps(storage, sm)
    init_dashboard_deps(storage)
    init_audit_deps(audit_logger)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_empty(client):
    resp = await client.get("/api/v1/admin/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["events"] == []
    assert data["total"] == 0
    assert data["limit"] == 100
    assert data["offset"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_with_events(client, audit_logger):
    event = AuditEvent(
        event_type=AuditEventType.AUTH,
        actor_id="admin",
        actor_role="admin",
        action="login",
        resource="dashboard",
        details={"ip": "10.0.0.1"},
    )
    await audit_logger.log_event(event)
    resp = await client.get("/api/v1/admin/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["events"]) >= 1
    ev = data["events"][0]
    assert ev["event_type"] == "auth"
    assert ev["actor_id"] == "admin"
    assert ev["action"] == "login"
    assert ev["details"] == {"ip": "10.0.0.1"}


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_filter_by_event_type(client, audit_logger):
    event = AuditEvent(
        event_type=AuditEventType.AGENT,
        actor_id="agent-1",
        action="register",
        resource="system",
    )
    await audit_logger.log_event(event)
    resp = await client.get(
        "/api/v1/admin/audit", params={"event_type": "agent"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["event_type"] == "agent" for e in data["events"])


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_filter_by_actor(client, audit_logger):
    resp = await client.get(
        "/api/v1/admin/audit", params={"actor_id": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["actor_id"] == "admin" for e in data["events"])


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_invalid_event_type(client):
    resp = await client.get(
        "/api/v1/admin/audit", params={"event_type": "invalid"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_audit_query_pagination(client, audit_logger):
    for i in range(5):
        await audit_logger.log_event(AuditEvent(
            event_type=AuditEventType.SYSTEM,
            actor_id=f"pager-{i}",
            action="test",
        ))
    resp = await client.get(
        "/api/v1/admin/audit", params={"limit": 2, "offset": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) <= 2
    assert data["limit"] == 2
    assert data["offset"] == 0
