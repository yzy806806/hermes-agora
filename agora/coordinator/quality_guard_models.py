"""Quality guard data models — enums and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QualityIssue(str, Enum):
    """Types of quality issues in discussions."""

    LOW_ARGUMENT_QUALITY = "low_argument_quality"
    EVIDENCE_SPARSE = "evidence_sparse"
    REPETITIVE_ARGUMENTS = "repetitive_arguments"
    SINGLE_PERSPECTIVE = "single_perspective"
    WEAK_REBUTTAL = "weak_rebuttal"


@dataclass
class QualityAlert:
    """A quality alert for a discussion."""

    issue: QualityIssue
    severity: float  # 0.0-1.0
    details: str
    affected_agents: list[str] = field(default_factory=list)


@dataclass
class QualityGuardConfig:
    """Configuration for quality guard checks."""

    min_content_length: int = 50
    evidence_sparse_threshold: float = 0.6
    repetitive_threshold: float = 0.3
    trivial_phrases: list[str] = field(
        default_factory=lambda: ["同意", "支持", "反对", "没意见", "是的"]
    )
