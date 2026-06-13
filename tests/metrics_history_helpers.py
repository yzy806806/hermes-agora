"""Shared fixtures & seed helpers for metrics history tests."""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agora.coordinator.main import create_app
from agora.coordinator.metrics_history_router import (
    init_metrics_history_deps,
)
from agora.coordinator.storage import Storage

NOW = "2026-06-13T12:00:00+00:00"
DAY_AGO = "2026-06-12T12:00:00+00:00"


async def seed_agents(storage):
    async with storage._connection() as db:
        await db.execute(
            "INSERT INTO agents(agent_id,name,registered_at,is_online)"
            " VALUES(?,?,?,?)", ["a1", "Agent1", NOW, 1],
        )
        await db.execute(
            "INSERT INTO agents(agent_id,name,registered_at,is_online)"
            " VALUES(?,?,?,?)", ["a2", "Agent2", DAY_AGO, 0],
        )
        await db.commit()


async def seed_tasks(storage):
    async with storage._connection() as db:
        await db.execute(
            "INSERT INTO motions(id,title,created_at,updated_at)"
            " VALUES('m1','Motion1',?,?)", [NOW, NOW],
        )
        await db.execute(
            "INSERT INTO task_graphs(id,motion_id,created_at)"
            " VALUES('g1','m1',?)", [NOW],
        )
        await db.execute(
            "INSERT INTO tasks(id,graph_id,motion_id,title,"
            "status,created_at,completed_at) VALUES(?,?,?,?,?,?,?)",
            ["t1", "g1", "m1", "Task1", "done", NOW, NOW],
        )
        await db.execute(
            "INSERT INTO tasks(id,graph_id,motion_id,title,"
            "status,created_at,completed_at) VALUES(?,?,?,?,?,?,?)",
            ["t2", "g1", "m1", "Task2", "done", DAY_AGO, DAY_AGO],
        )
        await db.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def mh_client(tmp_path):
    db_path = str(tmp_path / "mh_test.db")
    storage = Storage(db_path)
    await storage.init_db()
    init_metrics_history_deps(storage)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client, storage
