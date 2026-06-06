"""Tests for coordinator/memory_sync.py and coordinator/conclusion_types.py."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from coordinator.conclusion_types import DiscussionConclusion
from coordinator.memory_sync import MemorySync


def _make_storage(motion=None, votes=None, messages=None):
    """Create a mock storage with configurable return values."""
    storage = AsyncMock()
    storage.get_motion = AsyncMock(return_value=motion)
    storage.get_votes = AsyncMock(return_value=votes or [])
    storage.get_messages = AsyncMock(return_value=messages or [])
    return storage


def _closed_motion(**overrides):
    """Build a closed motion dict for testing."""
    base = {
        "id": "motion-1",
        "title": "Adopt microservice architecture",
        "description": "How to split the monolith",
        "status": "closed",
        "decision": "adopted",
        "rationale": "Team consensus on modularity",
        "action_items": '["Create service boundaries", "Set up CI"]',
        "voting_method": "simple_majority",
        "closed_at": "2026-06-01T10:00:00",
    }
    base.update(overrides)
    return base


class TestDiscussionConclusion:
    def test_to_dict(self):
        c = DiscussionConclusion(
            motion_id="m1", title="Test", decision="adopted",
            created_at="2026-06-01T10:00:00",
        )
        d = c.to_dict()
        assert d["type"] == "agora_conclusion"
        assert d["motion_id"] == "m1"
        assert d["decision"] == "adopted"
        assert "tags" not in d  # tags added by MemorySync

    def test_defaults(self):
        c = DiscussionConclusion(motion_id="m2", title="T", decision="rejected")
        assert c.key_points == []
        assert c.action_items == []
        assert c.votes_summary == {}
