"""Data classes for weighted voting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WeightSource(str, Enum):
    """Where a weight value comes from."""

    MANUAL = "manual"
    REPUTATION = "reputation"
    EXPERTISE = "expertise"
    STAKES = "stakes"


@dataclass
class AgentWeight:
    """Weight record for a single agent."""

    agent_id: str
    weight: float
    source: WeightSource = WeightSource.MANUAL
    reason: Optional[str] = None


@dataclass
class WeightedVoteResult:
    """Result of a weighted vote tally."""

    decision: str
    total_weight_yes: float = 0.0
    total_weight_no: float = 0.0
    total_weight_abstain: float = 0.0
    effective_yes: float = 0.0
    effective_no: float = 0.0
    threshold: float = 0.5
    rationale: str = ""
