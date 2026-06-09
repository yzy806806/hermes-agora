"""Similar topic detection for referencing historical conclusions.

Detects if a new motion title is similar to past discussion conclusions,
enabling automatic reference context generation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _is_cjk(char: str) -> bool:
    """Check if a character is CJK."""
    cp = ord(char)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def _split_text(text: str) -> list[str]:
    """Split text into tokens, handling both English and Chinese."""
    # Match English words or individual CJK characters
    tokens = re.findall(r"[a-zA-Z]+|[\u4e00-\u9fff]", text.lower())
    return tokens


class SimilarTopicDetector:
    """Similar topic detector using Jaccard similarity on keywords."""

    def __init__(
        self, memory_path: str = "~/.hermes/memories/discussion_conclusions"
    ) -> None:
        self.memory_path = memory_path
        self._index: dict[str, list[dict[str, Any]]] = {}

    async def find_similar(
        self, title: str, threshold: float = 0.6
    ) -> list[dict[str, Any]]:
        """Find similar historical conclusions."""
        title_keywords = self._extract_keywords(title)
        seen: set[str] = set()
        similar: list[dict[str, Any]] = []

        for tag, conclusions in self._load_conclusions().items():
            for conclusion in conclusions:
                mid = conclusion["motion_id"]
                if mid in seen:
                    continue
                score = self._calculate_similarity(
                    title_keywords, conclusion.get("tags", [])
                )
                if score >= threshold:
                    similar.append({
                        "motion_id": mid,
                        "title": conclusion["title"],
                        "decision": conclusion["decision"],
                        "rationale": conclusion.get("rationale", ""),
                        "similarity": score,
                        "key_points": conclusion.get("key_points", [])[:3],
                    })
                    seen.add(mid)

        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:5]

    def _extract_keywords(self, text: str) -> set[str]:
        """Extract keywords from text (English words + CJK chars)."""
        tokens = _split_text(text)
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were",
            "of", "in", "on", "at", "to", "for", "and", "or",
            "和", "的", "是", "在", "对", "与",
        }
        return {
            w for w in tokens
            if w not in stopwords
            and (len(w) > 1 or _is_cjk(w))
        }

    def _calculate_similarity(
        self, keywords1: set[str], tags: list[Any]
    ) -> float:
        """Calculate Jaccard similarity between keywords and tags."""
        if not keywords1 or not tags:
            return 0.0

        tag_set: set[str] = set()
        for t in tags:
            if isinstance(t, str):
                tag_tokens = _split_text(t)
                tag_set.update(tag_tokens)

        if not tag_set:
            return 0.0

        intersection = len(keywords1 & tag_set)
        union = len(keywords1 | tag_set)
        return intersection / union if union > 0 else 0.0

    def _load_conclusions(self) -> dict[str, list[dict[str, Any]]]:
        """Load historical conclusions from memory (cached)."""
        if self._index:
            return self._index

        conclusions_by_tag: dict[str, list[dict[str, Any]]] = {}
        memory_dir = Path(self.memory_path).expanduser()

        if not memory_dir.exists():
            return {}

        for year_dir in memory_dir.iterdir():
            if not year_dir.is_dir():
                continue
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for file in month_dir.glob("*.json"):
                    try:
                        data = json.loads(file.read_text(encoding="utf-8"))
                        for tag in data.get("tags", []):
                            conclusions_by_tag.setdefault(tag, []).append(data)
                    except (json.JSONDecodeError, OSError):
                        continue

        self._index = conclusions_by_tag
        return conclusions_by_tag

    async def generate_reference_context(self, title: str) -> str:
        """Generate reference context for a new motion."""
        similar = await self.find_similar(title)

        if not similar:
            return ""

        lines = ["【相关历史结论】"]
        for s in similar[:3]:
            lines.append(
                f"- {s['title']}: {s['decision']} (相似度 {s['similarity']:.0%})"
            )
            if s.get("rationale"):
                lines.append(f"  理由: {s['rationale'][:100]}...")

        return "\n".join(lines)
