"""Tests for coordinator/voting/weighted.py."""

from coordinator.voting.weighted import WeightedVoting
from coordinator.voting.weighted_types import WeightedVoteResult


class TestWeightedVoting:
    def setup_method(self):
        self.weights = {"agent_a": 2.0, "agent_b": 1.0, "agent_c": 1.0}
        self.wv = WeightedVoting(self.weights, threshold=0.5)

    def test_adopted(self):
        votes = [
            {"agent_id": "agent_a", "vote": "yes"},
            {"agent_id": "agent_b", "vote": "no"},
        ]
        r = self.wv.count(votes)
        assert r.decision == "adopted"
        assert r.total_weight_yes == 2.0
        assert r.total_weight_no == 1.0

    def test_rejected(self):
        votes = [
            {"agent_id": "agent_a", "vote": "no"},
            {"agent_id": "agent_b", "vote": "no"},
        ]
        r = self.wv.count(votes)
        assert r.decision == "rejected"

    def test_no_consensus(self):
        r = self.wv.count([])
        assert r.decision == "no_consensus"

    def test_abstain_only(self):
        votes = [{"agent_id": "agent_a", "vote": "abstain"}]
        r = self.wv.count(votes)
        assert r.decision == "no_consensus"
        # Early return on no yes/no votes, abstain not tracked separately
        assert r.total_weight_abstain == 0.0

    def test_confidence_adjusts_weight(self):
        votes = [
            {"agent_id": "agent_a", "vote": "no", "confidence": 0.5},
            {"agent_id": "agent_b", "vote": "yes"},
        ]
        r = self.wv.count(votes)
        # agent_a: 2.0 * 0.5 = 1.0 no; agent_b: 1.0 yes
        assert r.total_weight_yes == 1.0
        assert r.total_weight_no == 1.0

    def test_default_weight(self):
        votes = [
            {"agent_id": "unknown", "vote": "yes"},
            {"agent_id": "agent_a", "vote": "no"},
        ]
        r = self.wv.count(votes)
        # unknown weight=1.0 yes, agent_a weight=2.0 no
        assert r.decision == "rejected"

    def test_custom_threshold(self):
        wv = WeightedVoting(self.weights, threshold=0.8)
        votes = [
            {"agent_id": "agent_a", "vote": "yes"},
            {"agent_id": "agent_b", "vote": "no"},
        ]
        r = wv.count(votes)
        # 2/3 = 0.667 < 0.8
        assert r.decision == "rejected"
