"""Tests for quality guard checks — evidence, repetitive, rebuttal."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agora.coordinator.quality_guard import QualityGuard
from agora.coordinator.quality_guard_models import (
    QualityGuardConfig,
    QualityIssue,
)


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_messages = AsyncMock(return_value=[])
    return s


class TestEvidenceSparsity:
    @pytest.mark.asyncio
    async def test_evidence_sparse_alert(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": f"a{i}", "stance": "support",
             "content": "x" * 60, "evidence": []}
            for i in range(5)
        ] + [
            {"agent_id": "a5", "stance": "oppose",
             "content": "y" * 60, "evidence": [{"type": "data"}]}
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.EVIDENCE_SPARSE in issues

    @pytest.mark.asyncio
    async def test_evidence_sufficient_no_alert(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": "support",
             "content": "x" * 60, "evidence": [{"type": "data"}]},
            {"agent_id": "a2", "stance": "oppose",
             "content": "y" * 60, "evidence": [{"type": "data"}]},
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.EVIDENCE_SPARSE not in issues


class TestRepetitive:
    @pytest.mark.asyncio
    async def test_repetitive_detected(self, mock_storage):
        content = "This is the exact same argument repeated by many agents"
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": f"a{i}", "stance": "support",
             "content": content, "evidence": [{"type": "data"}]}
            for i in range(10)
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.REPETITIVE_ARGUMENTS in issues


class TestRebuttalStrength:
    @pytest.mark.asyncio
    async def test_weak_rebuttal_detected(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": f"a{i}", "stance": "support",
             "content": "x" * 60, "evidence": [{"type": "data"}]}
            for i in range(4)
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.WEAK_REBUTTAL in issues

    @pytest.mark.asyncio
    async def test_has_replies_no_alert(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"agent_id": "a1", "stance": "support",
             "content": "x" * 60, "reply_to": "a2",
             "evidence": [{"type": "data"}]},
            {"agent_id": "a2", "stance": "oppose",
             "content": "y" * 60, "evidence": [{"type": "data"}]},
        ])
        guard = QualityGuard(mock_storage)
        alerts = await guard.check_quality("m1")
        issues = {a.issue for a in alerts}
        assert QualityIssue.WEAK_REBUTTAL not in issues
