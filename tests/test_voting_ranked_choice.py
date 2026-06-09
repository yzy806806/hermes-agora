"""Tests for coordinator/voting/ranked_choice.py (IRV)."""

from agora.coordinator.voting.ranked_choice import RankedChoiceVoting


class TestRankedChoiceVoting:
    def setup_method(self):
        self.rcv = RankedChoiceVoting()

    def test_first_round_majority(self):
        ballots = [
            {"ranking": ["A", "B", "C"]},
            {"ranking": ["A", "C", "B"]},
            {"ranking": ["B", "A", "C"]},
        ]
        r = self.rcv.count(ballots)
        assert r["decision"] == "adopted"
        assert r["winner"] == "A"

    def test_irv_redistribution(self):
        # C eliminated first, then B gets C's second-choice votes
        ballots = [
            {"ranking": ["A", "B"]},
            {"ranking": ["A", "B"]},
            {"ranking": ["B", "A"]},
            {"ranking": ["C", "B"]},
            {"ranking": ["C", "B"]},
        ]
        r = self.rcv.count(ballots)
        # Round 1: A=2, B=1, C=2 -> no majority (5/2=2.5)
        # A and C tied at 2, B eliminated (min=1)
        # Then A=2, C=2 -> tie, or B eliminated then C voters go to B...
        # Actually: min=1 (B), eliminate B. Remaining=[A,C].
        # Round 2: A gets A-first(2) + B-second(A)(1)=3; C gets C-first(2)=2
        # A=3 > 2.5, A wins
        assert r["decision"] == "adopted"
        assert r["winner"] == "A"

    def test_no_votes(self):
        r = self.rcv.count([])
        assert r["decision"] == "no_consensus"

    def test_empty_rankings(self):
        r = self.rcv.count([{"ranking": []}])
        assert r["decision"] == "no_consensus"

    def test_tie(self):
        ballots = [
            {"ranking": ["A"]},
            {"ranking": ["B"]},
        ]
        r = self.rcv.count(ballots)
        assert r["decision"] == "tie"

    def test_single_candidate(self):
        ballots = [{"ranking": ["A"]}]
        r = self.rcv.count(ballots)
        assert r["decision"] == "adopted"
        assert r["winner"] == "A"
