"""Historical decision pattern analysis for the Agora Coordinator.

Learns from past decisions to suggest discussion strategies
(fast_track / deep_discussion / standard) for new motions.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from .storage import Storage

logger = logging.getLogger(__name__)


@dataclass
class DecisionPattern:
    """Aggregated decision pattern for a topic category."""

    topic_category: str
    decision: str
    avg_rounds: float
    consensus_level: str
    common_arguments: list[str] = field(default_factory=list)


class HistoryPattern:
    """Analyse historical decision patterns and suggest strategies."""

    _CATEGORY_KEYWORDS: dict[str, list[str]] = {
        "architecture": ["架构", "microservice", "service", "design", "系统设计"],
        "priority": ["优先级", "priority", "重要", "紧急"],
        "resource": ["资源", "resource", "预算", "成本", "人力"],
        "process": ["流程", "process", "方法", "规范"],
        "tooling": ["工具", "tool", "框架", "library"],
    }

    def __init__(self, storage: Storage, db_path: str) -> None:
        self.storage = storage
        self.db_path = db_path
        self._pattern_cache: dict[str, list[dict]] = {}
        self._cache_loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load_patterns(self) -> None:
        """Load historical patterns from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM motions
                WHERE status = 'closed' AND decision IS NOT NULL
                ORDER BY closed_at DESC LIMIT 100
            """) as cursor:
                rows = await cursor.fetchall()

        by_topic: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            cat = self._categorize_topic(row["title"])
            by_topic[cat].append(dict(row))

        self._pattern_cache = dict(by_topic)
        self._cache_loaded = True
        logger.info("Loaded %d patterns across %d categories",
                     len(rows), len(self._pattern_cache))

    async def get_pattern(self, topic: str) -> Optional[DecisionPattern]:
        """Return the decision pattern for *topic*'s category."""
        if not self._cache_loaded:
            await self.load_patterns()

        category = self._categorize_topic(topic)
        history = self._pattern_cache.get(category, [])
        if not history:
            return None

        decisions = [m["decision"] for m in history if m.get("decision")]
        rounds = [m.get("rounds", 3) for m in history]

        return DecisionPattern(
            topic_category=category,
            decision=max(set(decisions), key=decisions.count)
            if decisions else "no_consensus",
            avg_rounds=sum(rounds) / len(rounds) if rounds else 3.0,
            consensus_level=self._calc_consensus_level(history),
            common_arguments=self._extract_common_args(history),
        )

    async def suggest_strategy(self, topic: str) -> dict:
        """Suggest a discussion strategy based on historical patterns."""
        pattern = await self.get_pattern(topic)

        if not pattern:
            return {"strategy": "standard", "reason": "无历史数据"}

        strategy: dict = {
            "strategy": "standard",
            "suggested_rounds": int(pattern.avg_rounds),
            "expected_consensus": pattern.consensus_level,
            "recommendations": [],
        }

        if pattern.consensus_level == "high":
            strategy["strategy"] = "fast_track"
            strategy["recommendations"].append(
                "历史显示容易达成共识，可提前投票")
        elif pattern.consensus_level == "low":
            strategy["strategy"] = "deep_discussion"
            strategy["recommendations"].append(
                "历史显示分歧较大，建议引入更多论证")

        return strategy

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _categorize_topic(self, title: str) -> str:
        """Map a motion title to a broad category."""
        title_lower = title.lower()
        for cat, keywords in self._CATEGORY_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                return cat
        return "other"

    def _calc_consensus_level(self, history: list[dict]) -> str:
        """Derive consensus level from vote ratios in *history*."""
        yes_ratios: list[float] = []
        for h in history:
            raw = h.get("action_items", "[]")
            try:
                votes: dict = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            total = sum(votes.values())
            yes = votes.get("yes", 0)
            if total > 0:
                yes_ratios.append(yes / total)

        if not yes_ratios:
            return "unknown"
        avg = sum(yes_ratios) / len(yes_ratios)
        if avg >= 0.7:
            return "high"
        if avg >= 0.5:
            return "moderate"
        return "low"

    def _extract_common_args(self, history: list[dict]) -> list[str]:
        """Extract recurring rationale fragments (placeholder)."""
        return []
