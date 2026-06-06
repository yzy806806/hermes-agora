"""Tests for coordinator/voting/approval_voting.py."""

from coordinator.voting.approval_voting import ApprovalVoting


class TestApprovalVoting:
    def setup_method(self):
        self.av = ApprovalVoting()

    def test_adopted(self):
        votes = [
            {"approved": ["A", "B"]},
            {"approved": ["A"]},
            {"approved": ["A", "C"]},
        ]
        r = self.av.count(votes)
        assert r["decision"] == "adopted"
        assert r["winner"] == "A"
        assert r["results"]["A"] == 3

    def test_no_consensus(self):
        votes = [
            {"approved": ["A"]},
            {"approved": ["B"]},
            {"approved": ["C"]},
        ]
        r = self.av.count(votes)
        assert r["decision"] == "no_consensus"
        assert r["winner"] is None

    def test_no_votes(self):
        r = self.av.count([])
        assert r["decision"] == "no_consensus"

    def test_empty_approved(self):
        r = self.av.count([{"approved": []}])
        assert r["decision"] == "no_consensus"

    def test_multiple_approvals(self):
        votes = [
            {"approved": ["A", "B", "C"]},
            {"approved": ["A", "B"]},
        ]
        r = self.av.count(votes)
        assert r["results"]["A"] == 2
        assert r["results"]["B"] == 2
        assert r["results"]["C"] == 1

    def test_total_voters(self):
        votes = [
            {"approved": ["A"]},
            {"approved": ["B"]},
        ]
        r = self.av.count(votes)
        assert r["total_voters"] == 2
