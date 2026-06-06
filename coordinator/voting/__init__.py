"""Voting methods package for Agora Coordinator.

Provides multiple voting algorithms beyond simple majority:
weighted, multiple-choice, ranked-choice (IRV), range, and approval.
"""

from coordinator.voting.weighted import WeightedVoting
from coordinator.voting.weighted_types import (
    AgentWeight, WeightSource, WeightedVoteResult,
)
from coordinator.voting.multiple_choice import MultipleChoiceVote
from coordinator.voting.ranked_choice import RankedChoiceVoting
from coordinator.voting.range_voting import RangeVoting
from coordinator.voting.approval_voting import ApprovalVoting

__all__ = [
    "WeightedVoting", "WeightedVoteResult", "AgentWeight", "WeightSource",
    "MultipleChoiceVote", "RankedChoiceVoting", "RangeVoting",
    "ApprovalVoting",
]
