"""Multiple-choice voting — pick one from a list of options."""

from __future__ import annotations

from typing import Dict, List


class MultipleChoiceVote:
    """Tally votes where each voter picks exactly one option."""

    def __init__(self, options: List[str]):
        self.options = options

    def count(self, votes: List[dict]) -> dict:
        """Count votes. Each vote: {vote: <option>, ...}."""
        counts: Dict[str, int] = {opt: 0 for opt in self.options}
        abstain = 0

        for v in votes:
            choice = v.get("vote")
            if choice in counts:
                counts[choice] += 1
            elif choice == "abstain":
                abstain += 1

        total = sum(counts.values())
        if total == 0:
            return {"decision": "no_consensus", "results": counts,
                    "abstain": abstain, "rationale": "无有效投票"}

        winner = max(counts.items(), key=lambda x: x[1])

        if winner[1] > total / 2:
            dec = "adopted"
            rat = f"选项 {winner[0]} 获得简单多数：{winner[1]}/{total}"
        else:
            dec = "no_consensus"
            rat = f"最高票 {winner[0]} 未过半数：{winner[1]}/{total}"

        return {
            "decision": dec,
            "winner": winner[0] if dec == "adopted" else None,
            "results": counts,
            "abstain": abstain,
            "total": total,
            "rationale": rat,
        }
