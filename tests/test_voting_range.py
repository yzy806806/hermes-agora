"""Tests for coordinator/voting/range_voting.py."""

from agora.coordinator.voting.range_voting import RangeVoting


class TestRangeVoting:
    def setup_method(self):
        self.rv = RangeVoting(min_score=0, max_score=10)

    def test_adopted(self):
        votes = [
            {"scores": {"A": 9, "B": 3}},
            {"scores": {"A": 8, "B": 4}},
        ]
        r = self.rv.count(votes)
        assert r["decision"] == "adopted"
        assert r["winner"] == "A"
        assert r["results"]["A"]["average"] == 8.5

    def test_no_consensus_below_threshold(self):
        votes = [
            {"scores": {"A": 2, "B": 1}},
            {"scores": {"A": 3, "B": 2}},
        ]
        r = self.rv.count(votes)
        assert r["decision"] == "no_consensus"
        assert r["winner"] is None

    def test_no_votes(self):
        r = self.rv.count([])
        assert r["decision"] == "no_consensus"

    def test_empty_scores(self):
        r = self.rv.count([{"scores": {}}])
        assert r["decision"] == "no_consensus"

    def test_out_of_range_ignored(self):
        votes = [
            {"scores": {"A": 15, "B": 5}},  # 15 out of range
            {"scores": {"A": 8, "B": 6}},
        ]
        r = self.rv.count(votes)
        # A: only 8 counted (15 ignored), avg=8
        assert r["results"]["A"]["count"] == 1

    def test_custom_range(self):
        rv = RangeVoting(min_score=0, max_score=5)
        votes = [{"scores": {"A": 4}}]
        r = rv.count(votes)
        # threshold = 2.5, avg=4 >= 2.5
        assert r["decision"] == "adopted"

    def test_stats(self):
        votes = [
            {"scores": {"A": 3}},
            {"scores": {"A": 7}},
            {"scores": {"A": 5}},
        ]
        r = self.rv.count(votes)
        stats = r["results"]["A"]
        assert stats["min"] == 3
        assert stats["max"] == 7
        assert stats["count"] == 3
