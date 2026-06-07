"""Tests for coordinator/quality_scorer.py."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from coordinator.quality_scorer import QualityScore, QualityScorer


@pytest.fixture
def mock_storage():
    s = AsyncMock()
    s.get_messages = AsyncMock(return_value=[])
    return s


class TestQualityScore:
    def test_creation(self):
        qs = QualityScore(
            evidence_sufficiency=0.8,
            argument_logic=0.7,
            perspective_diversity=0.6,
            rebuttal_strength=0.5,
            overall=0.67,
        )
        assert qs.evidence_sufficiency == 0.8
        assert qs.argument_logic == 0.7
        assert qs.perspective_diversity == 0.6
        assert qs.rebuttal_strength == 0.5
        assert qs.overall == 0.67


class TestQualityScorer:
    @pytest.mark.asyncio
    async def test_empty_messages(self, mock_storage):
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.evidence_sufficiency == 0.0
        assert qs.argument_logic == 0.0
        assert qs.perspective_diversity == 0.0
        assert qs.rebuttal_strength == 0.0
        assert qs.overall == 0.0

    @pytest.mark.asyncio
    async def test_full_evidence(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x" * 200, "evidence": ["a"], "stance": "support"},
            {"content": "y" * 200, "evidence": ["b"], "stance": "oppose"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.evidence_sufficiency == 1.0

    @pytest.mark.asyncio
    async def test_no_evidence(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x" * 200, "stance": "support"},
            {"content": "y" * 200, "stance": "oppose"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.evidence_sufficiency == 0.0

    @pytest.mark.asyncio
    async def test_argument_logic_short(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "short", "stance": "support"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.argument_logic < 0.1

    @pytest.mark.asyncio
    async def test_argument_logic_long(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x" * 200, "stance": "support"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.argument_logic == 1.0

    @pytest.mark.asyncio
    async def test_diversity_single_stance(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x", "stance": "support"},
            {"content": "y", "stance": "support"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.perspective_diversity == pytest.approx(1 / 3, abs=0.01)

    @pytest.mark.asyncio
    async def test_diversity_three_stances(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x", "stance": "support"},
            {"content": "y", "stance": "oppose"},
            {"content": "z", "stance": "neutral"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.perspective_diversity == 1.0

    @pytest.mark.asyncio
    async def test_rebuttal_with_replies(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x", "reply_to": "a1", "stance": "support"},
            {"content": "y", "stance": "oppose"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        assert qs.rebuttal_strength == 0.5

    @pytest.mark.asyncio
    async def test_overall_weighted(self, mock_storage):
        mock_storage.get_messages = AsyncMock(return_value=[
            {"content": "x" * 200, "evidence": ["a"],
             "stance": "support", "reply_to": "a1"},
        ])
        scorer = QualityScorer()
        qs = await scorer.score("m1", mock_storage)
        expected = 1.0 * 0.3 + 1.0 * 0.3 + (1/3) * 0.2 + 1.0 * 0.2
        assert qs.overall == pytest.approx(expected, abs=0.01)
