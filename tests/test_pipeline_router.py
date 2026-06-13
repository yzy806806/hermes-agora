"""Tests for pipeline REST API (Phase 13.1e)."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agora.coordinator.main import create_app
from agora.coordinator.pipeline_router import init_pipeline_router_deps
from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def client(tmp_path):
    db_path = str(tmp_path / "pipeline_api.db")
    storage = Storage(db_path)
    await storage.init_db()
    init_pipeline_router_deps(storage)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c, storage


@pytest.mark.asyncio
async def test_start_pipeline(client):
    c, _ = client
    resp = await c.post("/api/v1/pipelines", json={
        "idea": "build auth", "project_id": "p1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == "p1"
    assert data["idea"] == "build auth"
    assert data["phase"] == "discussing"


@pytest.mark.asyncio
async def test_get_pipeline(client):
    c, _ = client
    created = await c.post("/api/v1/pipelines", json={
        "idea": "test", "project_id": "p1",
    })
    pid = created.json()["id"]
    resp = await c.get(f"/api/v1/pipelines/{pid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pid


@pytest.mark.asyncio
async def test_get_pipeline_not_found(client):
    c, _ = client
    resp = await c.get("/api/v1/pipelines/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_pipelines_count_is_total(client):
    c, _ = client
    # Create 5 pipelines for p1, 2 for p2
    for _ in range(5):
        await c.post("/api/v1/pipelines", json={"idea": "a", "project_id": "p1"})
    for _ in range(2):
        await c.post("/api/v1/pipelines", json={"idea": "b", "project_id": "p2"})
    # Request with limit=3 — count should be total, not len(items)
    resp = await c.get("/api/v1/pipelines", params={"project_id": "p1", "limit": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 5
    assert len(data["pipelines"]) == 3


@pytest.mark.asyncio
async def test_list_pipelines_filter(client):
    c, _ = client
    resp = await c.get("/api/v1/pipelines", params={"project_id": "p1"})
    assert resp.status_code == 200
    for p in resp.json()["pipelines"]:
        assert p["project_id"] == "p1"
