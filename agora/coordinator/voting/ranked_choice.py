"""Ranked-choice voting with Instant Runoff Voting (IRV) algorithm."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List


class RankedChoiceVoting:
    """Instant Runoff Voting: eliminate lowest-ranked until majority."""

    def count(self, ballots: List[dict]) -> dict:
        """Run IRV. Each ballot: {ranking: [option1, option2, ...]}."""
        if not ballots:
            return {"decision": "no_consensus", "rationale": "无投票"}

        # Extract all options
        all_opts = set()
        for b in ballots:
            all_opts.update(b.get("ranking", []))

        if not all_opts:
            return {"decision": "no_consensus", "rationale": "无效投票"}

        # Convert to rank dicts: option -> rank (lower = better)
        ranked = []
        for b in ballots:
            r = b.get("ranking", [])
            if r:
                ranked.append({opt: i for i, opt in enumerate(r)})

        return self._irv_iterate(ranked, list(all_opts))

    def _irv_iterate(self, ballots: List[Dict[str, int]],
                     remaining: List[str]) -> dict:
        """IRV elimination rounds."""
        while remaining:
            # Count first choices among remaining options
            first = Counter()
            for b in ballots:
                for opt in b:
                    if opt in remaining:
                        first[opt] += 1
                        break

            total = sum(first.values())
            if total == 0:
                return {"decision": "no_consensus", "rationale": "无有效选票"}

            # Check for majority
            for opt, cnt in first.most_common():
                if cnt > total / 2:
                    return {"decision": "adopted", "winner": opt,
                            "results": dict(first), "rationale":
                            f"{opt} 获得过半数：{cnt}/{total}"}

            # Eliminate lowest
            min_cnt = min(first.values())
            elim = [o for o, c in first.items() if c == min_cnt]

            if len(remaining) <= len(elim):
                return {"decision": "tie", "leading": first.most_common(3),
                        "rationale": f"平局：{elim}"}

            for o in elim:
                remaining.remove(o)

        return {"decision": "no_consensus", "rationale": "无法产生获胜者"}
