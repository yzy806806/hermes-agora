"""Tests for VoteCounterFactory and built-in counters."""

import pytest

from coordinator.models import VotingMethod
from coordinator.voting.factory import (
    VoteCounterFactory,
    SimpleMajorityCounter,
    SupermajorityCounter,
    UnanimousCounter,
)


class TestSimpleMajority:
    """Simple majority counter tests."""

    def test_adopted(self):
        votes = [
            {"vote": "yes"}, {"vote": "yes"}, {"vote": "no"},
        ]
        result = SimpleMajorityCounter().count(votes)
        assert result["decision"] == "adopted"

    def test_rejected(self):
        votes = [
            {"vote": "no"}, {"vote": "no"}, {"vote": "yes"},
        ]
        result = SimpleMajorityCounter().count(votes)
        assert result["decision"] == "rejected"

    def test_no_votes(self):
        result = SimpleMajorityCounter().count([])
        assert result["decision"] == "no_consensus"

    def test_tie_rejected(self):
        votes = [{"vote": "yes"}, {"vote": "no"}]
        result = SimpleMajorityCounter().count(votes)
        assert result["decision"] == "rejected"


class TestSupermajority:
    """Supermajority (2/3) counter tests."""

    def test_adopted(self):
        votes = [
            {"vote": "yes"}, {"vote": "yes"}, {"vote": "yes"},
        ]
        result = SupermajorityCounter().count(votes)
        assert result["decision"] == "adopted"

    def test_rejected(self):
        votes = [
            {"vote": "yes"}, {"vote": "no"}, {"vote": "no"},
        ]
        result = SupermajorityCounter().count(votes)
        assert result["decision"] == "rejected"

    def test_no_votes(self):
        result = SupermajorityCounter().count([])
        assert result["decision"] == "no_consensus"


class TestUnanimous:
    """Unanimous counter tests."""

    def test_adopted(self):
        votes = [{"vote": "yes"}, {"vote": "yes"}]
        result = UnanimousCounter().count(votes)
        assert result["decision"] == "adopted"

    def test_rejected(self):
        votes = [{"vote": "yes"}, {"vote": "no"}]
        result = UnanimousCounter().count(votes)
        assert result["decision"] == "rejected"

    def test_no_votes(self):
        result = UnanimousCounter().count([])
        assert result["decision"] == "no_consensus"


class TestFactory:
    """VoteCounterFactory registry tests."""

    def test_get_simple_majority(self):
        counter = VoteCounterFactory.get_counter(
            VotingMethod.SIMPLE_MAJORITY
        )
        assert isinstance(counter, SimpleMajorityCounter)

    def test_get_supermajority(self):
        counter = VoteCounterFactory.get_counter(
            VotingMethod.SUPERMAJORITY
        )
        assert isinstance(counter, SupermajorityCounter)

    def test_get_unanimous(self):
        counter = VoteCounterFactory.get_counter(VotingMethod.UNANIMOUS)
        assert isinstance(counter, UnanimousCounter)

    def test_unknown_defaults_to_simple(self):
        counter = VoteCounterFactory.get_counter(
            VotingMethod.BORDA_COUNT
        )
        assert isinstance(counter, SimpleMajorityCounter)

    def test_register_and_retrieve(self):
        class FakeCounter:
            def count(self, votes):
                return {"decision": "fake"}
        VoteCounterFactory.register(
            VotingMethod.BORDA_COUNT, FakeCounter()
        )
        counter = VoteCounterFactory.get_counter(VotingMethod.BORDA_COUNT)
        assert isinstance(counter, FakeCounter)

    def test_registered_methods(self):
        methods = VoteCounterFactory.registered_methods()
        assert VotingMethod.SIMPLE_MAJORITY in methods
