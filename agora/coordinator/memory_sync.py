"""MemorySync — sync discussion conclusions to Hermes memory.

Writes conclusions under ~/.hermes/memories/discussion_conclusions/
organized by year/month, with auto-generated tags for topic retrieval.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .conclusion_types import DiscussionConclusion

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were",
    "of", "in", "on", "at", "to", "for", "和", "的", "是",
})


class MemorySync:
    """讨论结论同步到 Hermes Memory."""

    def __init__(self, storage, memory_path: str = "~/.hermes/memories"):
        self.storage = storage
        self.memory_path = memory_path

    async def sync_conclusion(self, motion_id: str) -> bool:
        """同步讨论结论到 Hermes memory. Returns False if not closable."""
        motion = await self.storage.get_motion(motion_id)
        if not motion or motion.get("status") != "closed":
            logger.warning("Motion %s not closed, skip sync", motion_id)
            return False

        votes = await self.storage.get_votes(motion_id)
        messages = await self.storage.get_messages(motion_id)
        conclusion = self._build_conclusion(motion, votes, messages)
        await self._write_to_memory(conclusion)
        logger.info("Synced conclusion for motion %s", motion_id)
        return True

    def _build_conclusion(
        self, motion: dict, votes: list[dict], messages: list[dict],
    ) -> DiscussionConclusion:
        """Construct DiscussionConclusion from storage data."""
        action_raw = motion.get("action_items", "[]")
        if isinstance(action_raw, str):
            action_items = json.loads(action_raw)
        else:
            action_items = list(action_raw)

        return DiscussionConclusion(
            motion_id=motion["id"],
            title=motion["title"],
            decision=motion.get("decision", "no_consensus") or "no_consensus",
            rationale=motion.get("rationale", "") or "",
            key_points=self._extract_key_points(messages),
            action_items=action_items,
            participants=sorted({m.get("agent_id", "") for m in messages} - {""}),
            voting_method=motion.get("voting_method", "simple_majority"),
            votes_summary=self._summarize_votes(votes),
            created_at=str(motion.get("closed_at") or datetime.now(timezone.utc).isoformat()),
        )

    async def _write_to_memory(self, conclusion: DiscussionConclusion) -> None:
        """Write conclusion JSON to year/month directory."""
        memory_dir = Path(self.memory_path).expanduser() / "discussion_conclusions"
        dt = datetime.fromisoformat(conclusion.created_at)
        month_dir = memory_dir / str(dt.year) / f"{dt.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)

        content = conclusion.to_dict()
        content["tags"] = self._generate_tags(conclusion)

        file_path = month_dir / f"{conclusion.motion_id}.json"
        file_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_key_points(messages: list[dict], limit: int = 5) -> list[str]:
        """Extract key points — top longest substantive messages."""
        substantive = [m for m in messages if len(m.get("content", "")) > 50]
        substantive.sort(key=lambda m: len(m.get("content", "")), reverse=True)
        return [str(m.get("content", ""))[:200] for m in substantive[:limit]]

    @staticmethod
    def _summarize_votes(votes: list[dict]) -> dict:
        """Count votes by choice."""
        summary: dict[str, int] = {}
        for v in votes:
            choice = v.get("vote", "abstain")
            summary[choice] = summary.get(choice, 0) + 1
        return summary

    @staticmethod
    def _generate_tags(conclusion: DiscussionConclusion) -> list[str]:
        """Generate tags for similarity retrieval."""
        tags = [conclusion.decision, conclusion.voting_method]
        words = re.findall(r"\w+", conclusion.title.lower())
        keywords = [w for w in words if len(w) > 2 and w not in _STOPWORDS][:5]
        tags.extend(keywords)
        return tags
