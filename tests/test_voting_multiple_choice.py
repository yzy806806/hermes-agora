"""Tests for coordinator/voting/multiple_choice.py."""

from coordinator.voting.multiple_choice import MultipleChoiceVote


class TestMultipleChoiceVote:
    def setup_method(self):
        self.options = ["alpha", "beta", "gamma"]
        self.mcv = MultipleChoiceVote(self.options)

    def test_majority_winner(self):
        votes = [
            {"vote": "alpha"},
            {"vote": "alpha"},
            {"vote": "beta"},
        ]
        r = self.mcv.count(votes)
        assert r["decision"] == "adopted"
        assert r["winner"] == "alpha"
        assert r["results"]["alpha"] == 2

    def test_no_majority(self):
        votes = [
            {"vote": "alpha"},
            {"vote": "beta"},
            {"vote": "gamma"},
        ]
        r = self.mcv.count(votes)
        assert r["decision"] == "no_consensus"
        assert r["winner"] is None

    def test_no_votes(self):
        r = self.mcv.count([])
        assert r["decision"] == "no_consensus"

    def test_abstain(self):
        votes = [
            {"vote": "alpha"},
            {"vote": "abstain"},
            {"vote": "abstain"},
        ]
        r = self.mcv.count(votes)
        assert r["decision"] == "adopted"
        assert r["abstain"] == 2

    def test_all_abstain(self):
        votes = [{"vote": "abstain"}] * 3
        r = self.mcv.count(votes)
        assert r["decision"] == "no_consensus"
        assert r["abstain"] == 3

    def test_invalid_option_ignored(self):
        votes = [
            {"vote": "alpha"},
            {"vote": "delta"},  # not in options
        ]
        r = self.mcv.count(votes)
        assert r["results"]["alpha"] == 1
        assert r["total"] == 1
