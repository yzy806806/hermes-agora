"""Vote counter factory for the Agora Coordinator.

Provides a registry-based factory that maps VotingMethod enum values
to their corresponding counter implementations. Ships with built-in
binary counters; advanced methods can be registered at runtime.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Protocol

from ..models import VotingMethod

logger = logging.getLogger(__name__)


class VoteCounter(Protocol):
    """Protocol for vote counter implementations."""

    def count(self, votes: list[dict]) -> dict:
        """Count votes and return a result dict."""
        ...


class SimpleMajorityCounter:
    """Simple majority (>50%) vote counter."""

    def count(self, votes: list[dict]) -> dict:
        tally: Counter = Counter()
        for v in votes:
            tally[v.get("vote", "abstain")] += 1
        total = sum(tally.values())
        if total == 0:
            return {"decision": "no_consensus", "rationale": "No votes"}
        yes = tally.get("yes", 0)
        no = tally.get("no", 0)
        if yes > no:
            return {"decision": "adopted", "results": dict(tally),
                    "rationale": f"Majority: {yes}/{total}"}
        return {"decision": "rejected", "results": dict(tally),
                "rationale": f"Rejected: {no}/{total} against"}


class SupermajorityCounter:
    """Supermajority (2/3) vote counter."""

    def count(self, votes: list[dict]) -> dict:
        tally: Counter = Counter()
        for v in votes:
            tally[v.get("vote", "abstain")] += 1
        total = tally.get("yes", 0) + tally.get("no", 0)
        if total == 0:
            return {"decision": "no_consensus", "rationale": "No votes"}
        ratio = tally.get("yes", 0) / total
        if ratio >= 2 / 3:
            return {"decision": "adopted", "results": dict(tally),
                    "rationale": f"Supermajority: {ratio:.0%}"}
        return {"decision": "rejected", "results": dict(tally),
                "rationale": f"Below 2/3: {ratio:.0%}"}


class UnanimousCounter:
    """Unanimous consent vote counter."""

    def count(self, votes: list[dict]) -> dict:
        tally: Counter = Counter()
        for v in votes:
            tally[v.get("vote", "abstain")] += 1
        total = tally.get("yes", 0) + tally.get("no", 0)
        if total == 0:
            return {"decision": "no_consensus", "rationale": "No votes"}
        no = tally.get("no", 0)
        if no == 0 and tally.get("yes", 0) > 0:
            return {"decision": "adopted", "results": dict(tally),
                    "rationale": "Unanimous consent"}
        return {"decision": "rejected", "results": dict(tally),
                "rationale": f"{no} objection(s)"}


class VoteCounterFactory:
    """Registry-based factory for vote counter instances."""

    _counters: dict[VotingMethod, VoteCounter] = {}

    @classmethod
    def register(cls, method: VotingMethod, counter: VoteCounter) -> None:
        """Register a counter for a voting method."""
        cls._counters[method] = counter

    @classmethod
    def get_counter(cls, method: VotingMethod) -> VoteCounter:
        """Return the counter for a method (default: simple majority)."""
        return cls._counters.get(method, SimpleMajorityCounter())

    @classmethod
    def registered_methods(cls) -> list[VotingMethod]:
        """Return all registered voting methods."""
        return list(cls._counters.keys())


# Register built-in binary counters
VoteCounterFactory.register(
    VotingMethod.SIMPLE_MAJORITY, SimpleMajorityCounter())
VoteCounterFactory.register(
    VotingMethod.SUPERMAJORITY, SupermajorityCounter())
VoteCounterFactory.register(
    VotingMethod.UNANIMOUS, UnanimousCounter())
