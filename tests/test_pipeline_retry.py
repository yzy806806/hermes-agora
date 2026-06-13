"""Tests for pipeline cancel/retry endpoints (Phase 13.1e)."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agora.coordinator.main import create_app
from agora.coordinator.pipeline_router import init_pipeline_router_deps
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def client(tmp_path):
    db_path = str(tmp_path / "pipeline_cancel_retry.db")
    storage = Storage(db_path)
    await storage.init_db()
    init_pipeline_router_deps(storage)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, storage


@pytest.mark.asyncio
async def test_cancel_pipeline(client):
    c, _ = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "cancel me", "project_id": "p1",
    })
    pid = created.json()["id"]
    resp = await c.post(f"/api/v1/pipelines/{pid}/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "failed"
    assert data["failed_phase"] == "discussing"


@pytest.mark.asyncio
async def test_cancel_terminal_pipeline(client):
    c, _ = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "done", "project_id": "p1",
    })
    pid = created.json()["id"]
    await c.post(f"/api/v1/pipelines/{pid}/cancel")
    resp = await c.post(f"/api/v1/pipelines/{pid}/cancel")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_retry_non_failed_pipeline(client):
    c, _ = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "active", "project_id": "p1",
    })
    pid = created.json()["id"]
    resp = await c.post(f"/api/v1/pipelines/{pid}/retry")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_retry_failed_retryable_pipeline(client):
    c, storage = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "fail and retry", "project_id": "p1",
    })
    pid = created.json()["id"]
    # Simulate failure during 'executing' phase (which is retryable)
    await storage.update_pipeline_run(pid, {"phase": "executing"})
    await c.post(f"/api/v1/pipelines/{pid}/cancel")
    row = await storage.get_pipeline_run(pid)
    assert row["failed_phase"] == "executing"
    # executing is in retryable_phases, so retry should succeed
    resp = await c.post(f"/api/v1/pipelines/{pid}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phase"] == "discussing"
    assert data["error"] is None


@pytest.mark.asyncio
async def test_retry_failed_non_retryable_pipeline(client):
    c, storage = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "non-retryable", "project_id": "p1",
    })
    pid = created.json()["id"]
    # Simulate failure during 'discussing' (not in retryable_phases)
    await c.post(f"/api/v1/pipelines/{pid}/cancel")
    # discussing is NOT retryable — should get 400
    resp = await c.post(f"/api/v1/pipelines/{pid}/retry")
    assert resp.status_code == 400
    assert "not retryable" in resp.json()["detail"]
