"""Tests for metrics history API — range filtering & empty data (Phase 13.3d)."""
import pytest
from metrics_history_helpers import mh_client


@pytest.mark.asyncio
async def test_range_1d_7d_30d(mh_client):
    client, _ = mh_client
    for rng in ("1d", "7d", "30d"):
        resp = await client.get(
            "/api/v1/metrics/history",
            params={"metric": "agent_activity", "range": rng},
        )
        assert resp.status_code == 200
        assert resp.json()["range"] == rng


@pytest.mark.asyncio
async def test_range_1h_and_6h(mh_client):
    client, _ = mh_client
    for rng in ("1h", "6h"):
        resp = await client.get(
            "/api/v1/metrics/history",
            params={"metric": "agent_activity", "range": rng},
        )
        assert resp.status_code == 200
        assert resp.json()["range"] == rng


@pytest.mark.asyncio
async def test_empty_data_all_metrics(mh_client):
    client, _ = mh_client
    for m in ("agent_activity", "task_throughput",
              "discussion_outcomes", "pipeline_success_rate",
              "rate_limit_usage"):
        resp = await client.get(
            "/api/v1/metrics/history",
            params={"metric": m, "range": "7d"},
        )
        d = resp.json()
        assert d["labels"] == []
        assert all(len(ds["data"]) == 0 for ds in d["datasets"])


@pytest.mark.asyncio
async def test_project_id_filter_accepted(mh_client):
    client, _ = mh_client
    resp = await client.get(
        "/api/v1/metrics/history",
        params={"metric": "task_throughput", "range": "7d",
                "project_id": "proj-1"},
    )
    assert resp.status_code == 200
    assert resp.json()["metric"] == "task_throughput"
