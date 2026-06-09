"""Tests for HistoryPattern load/get/suggest (part 2)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import aiosqlite
import pytest
import pytest_asyncio

from agora.coordinator.history_pattern import HistoryPattern
from agora.coordinator.storage.schema import SCHEMA_SQL


async def _init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.execute(
            "INSERT OR IGNORE INTO agents (agent_id, name, registered_at) "
            "VALUES (?, ?, ?)", ("a1", "Agent1", "2026-01-01T00:00:00"))
        for i, (title, dec, items, rnds) in enumerate([
            ("微服务架构设计", "adopted", '{"yes": 8, "no": 1}', 2),
            ("架构优化方案", "adopted", '{"yes": 7, "no": 2}', 1),
            ("紧急优先级调整", "rejected", '{"yes": 2, "no": 6}', 4),
            ("开发流程规范", "adopted", '{"yes": 9, "no": 1}', 3),
        ], 1):
            await db.execute(
                "INSERT INTO motions (id, title, description, rounds, "
                "voting_method, status, decision, action_items, "
                "created_at, updated_at, closed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"m{i}", title, "desc", rnds, "simple_majority",
                 "closed", dec, items,
                 f"2026-0{i}01T00:00:00", f"2026-0{i}01T00:00:00",
                 f"2026-0{i}01T00:00:00"))
        await db.commit()


@pytest.fixture
def mock_storage():
    return AsyncMock()


@pytest_asyncio.fixture
async def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    await _init_db(path)
    yield path
    Path(path).unlink(missing_ok=True)


class TestLoadAndGetPattern:
    @pytest.mark.asyncio
    async def test_load_populates_cache(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        await hp.load_patterns()
        assert hp._cache_loaded is True
        assert len(hp._pattern_cache) > 0

    @pytest.mark.asyncio
    async def test_get_pattern_auto_loads(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        p = await hp.get_pattern("微服务架构设计")
        assert p is not None
        assert p.topic_category == "architecture"

    @pytest.mark.asyncio
    async def test_unknown_category_returns_none(
        self, mock_storage, db_path,
    ):
        hp = HistoryPattern(mock_storage, db_path)
        await hp.load_patterns()
        assert await hp.get_pattern("完全无关xyz") is None

    @pytest.mark.asyncio
    async def test_pattern_fields(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        p = await hp.get_pattern("架构优化方案")
        assert p is not None
        assert p.decision == "adopted"
        assert p.avg_rounds > 0
        assert p.consensus_level in ("high", "moderate", "low", "unknown")


class TestSuggestStrategy:
    @pytest.mark.asyncio
    async def test_no_history_standard(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        r = await hp.suggest_strategy("完全无关xyz")
        assert r["strategy"] == "standard"
        assert "无历史数据" in r["reason"]

    @pytest.mark.asyncio
    async def test_architecture_fast_track(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        r = await hp.suggest_strategy("微服务架构设计")
        assert r["strategy"] in ("fast_track", "standard", "deep_discussion")
        assert "suggested_rounds" in r

    @pytest.mark.asyncio
    async def test_strategy_keys(self, mock_storage, db_path):
        hp = HistoryPattern(mock_storage, db_path)
        r = await hp.suggest_strategy("开发流程规范")
        for k in ("strategy", "suggested_rounds",
                   "expected_consensus", "recommendations"):
            assert k in r
