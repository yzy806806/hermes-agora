"""Data structures for the judgment accuracy tracking module."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentScore:
    """Agent judgment accuracy score."""

    agent_id: str
    total_decisions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    avg_confidence: float = 0.0
    recent_trend: list[int] = field(default_factory=list)
