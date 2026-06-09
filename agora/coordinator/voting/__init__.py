"""Voting methods package for Agora Coordinator.

Provides multiple voting algorithms beyond simple majority:
weighted, multiple-choice, ranked-choice (IRV), range, and approval.
"""

from .weighted import WeightedVoting
from .weighted_types import (
    AgentWeight, WeightSource, WeightedVoteResult,
)
from .multiple_choice import MultipleChoiceVote
from .ranked_choice import RankedChoiceVoting
from .range_voting import RangeVoting
from .approval_voting import ApprovalVoting

__all__ = [
    "WeightedVoting", "WeightedVoteResult", "AgentWeight", "WeightSource",
    "MultipleChoiceVote", "RankedChoiceVoting", "RangeVoting",
    "ApprovalVoting",
]
