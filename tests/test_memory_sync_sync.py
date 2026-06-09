"""Tests for MemorySync class — sync, file writing, helpers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from agora.coordinator.memory_sync import MemorySync


def _make_storage(motion=None, votes=None, messages=None):
    storage = AsyncMock()
    storage.get_motion = AsyncMock(return_value=motion)
    storage.get_votes = AsyncMock(return_value=votes or [])
    storage.get_messages = AsyncMock(return_value=messages or [])
    return storage


def _closed_motion(**overrides):
    base = {
        "id": "motion-1", "title": "Adopt microservice architecture",
        "status": "closed", "decision": "adopted",
        "rationale": "Team consensus", "action_items": '["Task A"]',
        "voting_method": "simple_majority",
        "closed_at": "2026-06-01T10:00:00",
    }
    base.update(overrides)
    return base


class TestSyncConclusion:
    @pytest.mark.asyncio
    async def test_sync_writes_file(self, tmp_path):
        mem = tmp_path / "mem"
        storage = _make_storage(
            motion=_closed_motion(),
            votes=[{"agent_id": "a1", "vote": "yes"}],
            messages=[{"agent_id": "a1", "content": "x" * 60}],
        )
        ms = MemorySync(storage, memory_path=str(mem))
        ok = await ms.sync_conclusion("motion-1")
        assert ok is True

        f = mem / "discussion_conclusions" / "2026" / "06" / "motion-1.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert data["decision"] == "adopted"
        assert "tags" in data

    @pytest.mark.asyncio
    async def test_skip_non_closed(self, tmp_path):
        storage = _make_storage(motion=_closed_motion(status="voting"))
        ms = MemorySync(storage, memory_path=str(tmp_path))
        assert await ms.sync_conclusion("motion-1") is False

    @pytest.mark.asyncio
    async def test_skip_missing_motion(self, tmp_path):
        storage = _make_storage(motion=None)
        ms = MemorySync(storage, memory_path=str(tmp_path))
        assert await ms.sync_conclusion("nope") is False
