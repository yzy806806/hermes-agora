"""Tests for coordinator/history_pattern.py."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import aiosqlite
import pytest
import pytest_asyncio

from coordinator.history_pattern import DecisionPattern, HistoryPattern
from coordinator.storage.schema import SCHEMA_SQL


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

async def _init_db(db_path: str) -> None:
    """Create tables and insert sample closed motions."""
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.execute(
            "INSERT OR IGNORE INTO agents (agent_id, name, registered_at) "
            "VALUES (?, ?, ?)", ("a1", "Agent1", "2026-01-01T00:00:00"))
        samples = [
            ("微服务架构设计", "adopted", '{"yes": 8, "no": 1}', 2),
            ("架构优化方案", "adopted", '{"yes": 7, "no": 2}', 1),
            ("紧急优先级调整", "rejected", '{"yes": 2, "no": 6}', 4),
            ("资源分配方案", "no_consensus", '{"yes": 3, "no": 3}', 5),
            ("开发流程规范", "adopted", '{"yes": 9, "no": 1}', 3),
            ("CI工具选型", "adopted", '{"yes": 6, "no": 3}', 2),
        ]
        for i, (title, dec, items, rounds) in enumerate(samples, 1):
            await db.execute(
                "INSERT INTO motions (id, title, description, rounds, "
                "voting_method, status, decision, action_items, "
                "created_at, updated_at, closed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (f"m{i}", title, "desc", rounds, "simple_majority",
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


# ---------------------------------------------------------------------------
# DecisionPattern dataclass
# ---------------------------------------------------------------------------

class TestDecisionPattern:
    def test_defaults(self):
        p = DecisionPattern(
            topic_category="architecture", decision="adopted",
            avg_rounds=2.5, consensus_level="high")
        assert p.common_arguments == []


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------

class TestCategorizeTopic:
    @pytest.fixture
    def hp(self, mock_storage):
        return HistoryPattern(mock_storage, ":memory:")

    @pytest.mark.parametrize("title,expected", [
        ("微服务架构设计", "architecture"),
        ("优先级调整", "priority"),
        ("资源分配方案", "resource"),
        ("开发流程规范", "process"),
        ("CI工具选型", "tooling"),
        ("随机话题", "other"),
    ])
    def test_categorize(self, hp, title, expected):
        assert hp._categorize_topic(title) == expected
