"""Tests for coordinator/quality_guard.py and quality_guard_checks.py."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agora.coordinator.quality_guard import QualityGuard
from agora.coordinator.quality_guard_models import (
    QualityAlert,
    QualityGuardConfig,
    QualityIssue,
)


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_messages = AsyncMock(return_value=[])
    return s


class TestQualityGuardConfig:
    def test_defaults(self):
        c = QualityGuardConfig()
        assert c.min_content_length == 50
        assert c.evidence_sparse_threshold == 0.6
        assert c.repetitive_threshold == 0.3
        assert len(c.trivial_phrases) > 0


class TestQualityIssue:
    def test_all_issues_defined(self):
        expected = [
            "LOW_ARGUMENT_QUALITY", "EVIDENCE_SPARSE",
            "REPETITIVE_ARGUMENTS", "SINGLE_PERSPECTIVE", "WEAK_REBUTTAL",
        ]
        for name in expected:
            assert hasattr(QualityIssue, name)


class TestQualityAlert:
    def test_creation(self):
        alert = QualityAlert(
            issue=QualityIssue.SINGLE_PERSPECTIVE,
            severity=0.9,
            details="test",
            affected_agents=["a1"],
        )
        assert alert.issue == QualityIssue.SINGLE_PERSPECTIVE
        assert alert.severity == 0.9
        assert alert.affected_agents == ["a1"]


class TestQualityGuard:
    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self, mock_storage):
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        assert alerts == []

    @pytest.mark.asyncio
    async def test_single_perspective_detected(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": "support", "content": "x" * 60},
            {"agent_id": "a2", "stance": "support", "content": "y" * 60},
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.SINGLE_PERSPECTIVE in issues

    @pytest.mark.asyncio
    async def test_low_argument_quality_short(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": "support", "content": "short"},
            {"agent_id": "a2", "stance": "oppose", "content": "x" * 60},
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.LOW_ARGUMENT_QUALITY in issues

    @pytest.mark.asyncio
    async def test_low_argument_quality_trivial(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": "support", "content": "同意"},
            {"agent_id": "a2", "stance": "oppose", "content": "x" * 60},
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.LOW_ARGUMENT_QUALITY in issues
