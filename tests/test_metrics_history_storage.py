"""Tests for metrics history storage queries (Phase 13.3a)."""
import pytest
import pytest_asyncio

from agora.coordinator.storage import Storage


@pytest_asyncio.fixture(loop_scope="session")
async def mh_storage(tmp_path):
    db_path = str(tmp_path / "mh_store.db")
    storage = Storage(db_path)
    await storage.init_db()
    return storage


@pytest.mark.asyncio
async def test_agent_activity_query(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_agent_activity", "7d")
    assert "labels" in result
    assert "datasets" in result


@pytest.mark.asyncio
async def test_task_throughput_query(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_task_throughput", "1d")
    assert isinstance(result["labels"], list)
    assert len(result["datasets"]) >= 1


@pytest.mark.asyncio
async def test_discussion_outcomes_query(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_discussion_outcomes", "30d")
    assert "labels" in result
    assert "datasets" in result


@pytest.mark.asyncio
async def test_pipeline_success_rate_query(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_pipeline_success_rate", "7d")
    assert isinstance(result["datasets"], list)


@pytest.mark.asyncio
async def test_rate_limit_usage_query(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_rate_limit_usage", "7d")
    assert "labels" in result
    assert "datasets" in result


@pytest.mark.asyncio
async def test_unknown_metric_returns_empty(mh_storage):
    result = await mh_storage.query_metrics_history(
        "query_nonexistent", "7d")
    assert result == {"labels": [], "datasets": []}


@pytest.mark.asyncio
async def test_all_range_keys(mh_storage):
    for rk in ("1d", "7d", "30d"):
        result = await mh_storage.query_metrics_history(
            "query_agent_activity", rk)
        assert "labels" in result
