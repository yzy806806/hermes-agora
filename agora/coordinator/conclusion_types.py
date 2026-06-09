"""DiscussionConclusion data structure for Agora memory sync."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DiscussionConclusion:
    """讨论结论数据结构 — 讨论结束后持久化到 Hermes memory."""

    motion_id: str
    title: str
    decision: str  # adopted / rejected / no_consensus
    rationale: str = ""
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    voting_method: str = "simple_majority"
    votes_summary: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict (tags added by MemorySync)."""
        return {
            "type": "agora_conclusion",
            "motion_id": self.motion_id,
            "title": self.title,
            "decision": self.decision,
            "rationale": self.rationale,
            "key_points": self.key_points,
            "action_items": self.action_items,
            "participants": self.participants,
            "voting_method": self.voting_method,
            "votes_summary": self.votes_summary,
            "timestamp": self.created_at,
        }
