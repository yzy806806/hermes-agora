"""Tests for coordinator/assessment.py."""

import pytest
from agora.coordinator.assessment import (
    Assessment,
    AssessmentResult,
    ConsensusDetector,
    ConsensusLevel,
    DiscussionMetrics,
    QualityAssessor,
)
from agora.coordinator.models import Stance


# ---- ConsensusDetector ----

class TestConsensusDetector:
    def setup_method(self):
        self.detector = ConsensusDetector()

    def test_empty_messages(self):
        level, counts = self.detector.detect([])
        assert level == ConsensusLevel.LOW
        assert counts == {}

    def test_high_consensus(self):
        msgs = [{"stance": "support"}] * 7 + [{"stance": "oppose"}] * 3
        level, counts = self.detector.detect(msgs)
        assert level == ConsensusLevel.HIGH

    def test_moderate_support(self):
        msgs = [{"stance": "support"}] * 5 + [{"stance": "oppose"}] * 5
        level, _ = self.detector.detect(msgs)
        assert level == ConsensusLevel.MODERATE

    def test_moderate_oppose(self):
        msgs = [{"stance": "oppose"}] * 6 + [{"stance": "neutral"}] * 4
        level, _ = self.detector.detect(msgs)
        assert level == ConsensusLevel.MODERATE

    def test_fractured(self):
        msgs = [{"stance": "support"}] * 4 + [{"stance": "oppose"}] * 4 + [{"stance": "neutral"}] * 2
        level, _ = self.detector.detect(msgs)
        assert level == ConsensusLevel.FRACTURED

    def test_low_consensus(self):
        msgs = [{"stance": "neutral"}] * 9 + [{"stance": "support"}] * 1
        level, _ = self.detector.detect(msgs)
        assert level == ConsensusLevel.LOW

    def test_no_valid_stances(self):
        level, counts = self.detector.detect([{"stance": None}])
        assert level == ConsensusLevel.LOW


# ---- QualityAssessor helpers ----

class TestQualityAssessorHelpers:
    def setup_method(self):
        self.assessor = QualityAssessor()

    def test_assess_argument_quality_empty(self):
        assert self.assessor._assess_argument_quality([]) == 0.0

    def test_assess_argument_quality_with_evidence(self):
        msgs = [
            {"content": "x" * 200, "evidence": ["a"]},
            {"content": "y" * 200, "evidence": ["b", "c"]},
        ]
        score = self.assessor._assess_argument_quality(msgs)
        assert 0.0 < score <= 1.0

    def test_make_decision_high_consensus(self):
        metrics = DiscussionMetrics(10, {}, 0.8, 0.8)
        result = self.assessor._make_decision(ConsensusLevel.HIGH, metrics, 10)
        assert result.result == AssessmentResult.CONSENSUS_REACHED

    def test_make_decision_fractured_low_quality(self):
        metrics = DiscussionMetrics(5, {}, 0.3, 0.8)
        result = self.assessor._make_decision(ConsensusLevel.FRACTURED, metrics, 5)
        assert result.result == AssessmentResult.NEEDS_MORE

    def test_make_decision_off_topic(self):
        metrics = DiscussionMetrics(8, {}, 0.6, 0.3)
        result = self.assessor._make_decision(ConsensusLevel.MODERATE, metrics, 8)
        assert result.result == AssessmentResult.OFF_TOPIC

    def test_make_decision_sufficient(self):
        metrics = DiscussionMetrics(8, {}, 0.7, 0.8)
        result = self.assessor._make_decision(ConsensusLevel.MODERATE, metrics, 8)
        assert result.result == AssessmentResult.SUFFICIENT

    def test_make_decision_needs_more(self):
        metrics = DiscussionMetrics(3, {}, 0.3, 0.8)
        result = self.assessor._make_decision(ConsensusLevel.LOW, metrics, 3)
        assert result.result == AssessmentResult.NEEDS_MORE
