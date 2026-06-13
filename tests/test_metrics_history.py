"""Tests for metrics history API — format & aggregation (Phase 13.3d)."""
import pytest
from metrics_history_helpers import mh_client, seed_agents, seed_tasks


@pytest.mark.asyncio
async def test_response_format_agent_activity(mh_client):
    client, _ = mh_client
    resp = await client.get(
        "/api/v1/metrics/history",
        params={"metric": "agent_activity", "range": "7d"},
    )
    assert resp.status_code == 200
    d = resp.json()
    assert d["metric"] == "agent_activity"
    assert d["range"] == "7d"
    assert isinstance(d["labels"], list)
    for ds in d["datasets"]:
        assert "label" in ds and "data" in ds


@pytest.mark.asyncio
async def test_response_format_all_metrics(mh_client):
    client, _ = mh_client
    for m in ("task_throughput", "discussion_outcomes",
              "pipeline_success_rate", "rate_limit_usage"):
        resp = await client.get(
            "/api/v1/metrics/history",
            params={"metric": m, "range": "7d"},
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["metric"] == m
        assert "labels" in d and "datasets" in d


@pytest.mark.asyncio
async def test_agent_activity_with_data(mh_client):
    client, storage = mh_client
    await seed_agents(storage)
    resp = await client.get(
        "/api/v1/metrics/history",
        params={"metric": "agent_activity", "range": "7d"},
    )
    d = resp.json()
    assert len(d["labels"]) >= 1
    assert any(len(ds["data"]) >= 1 for ds in d["datasets"])


@pytest.mark.asyncio
async def test_task_throughput_with_data(mh_client):
    client, storage = mh_client
    await seed_tasks(storage)
    resp = await client.get(
        "/api/v1/metrics/history",
        params={"metric": "task_throughput", "range": "7d"},
    )
    d = resp.json()
    assert len(d["labels"]) >= 1
    assert d["datasets"][0]["label"] == "Completed"
