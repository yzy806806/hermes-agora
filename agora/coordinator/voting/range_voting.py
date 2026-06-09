"""Range voting — score each option on a numeric scale."""

from __future__ import annotations

from typing import Dict, List


class RangeVoting:
    """Score each option 0–max_score; highest average wins."""

    def __init__(self, min_score: int = 0, max_score: int = 10):
        self.min_score = min_score
        self.max_score = max_score

    def count(self, votes: List[dict]) -> dict:
        """Tally range votes. Each vote: {scores: {option: score}}."""
        if not votes:
            return {"decision": "no_consensus", "rationale": "无投票"}

        # Collect all options
        all_opts: set[str] = set()
        for v in votes:
            all_opts.update(v.get("scores", {}).keys())

        if not all_opts:
            return {"decision": "no_consensus", "rationale": "无效投票"}

        # Gather scores per option
        totals: Dict[str, List[float]] = {o: [] for o in all_opts}
        for v in votes:
            for opt, score in v.get("scores", {}).items():
                if self.min_score <= score <= self.max_score:
                    totals[opt].append(score)

        # Compute stats
        results = {}
        for opt, scores in totals.items():
            if scores:
                results[opt] = {
                    "total": sum(scores),
                    "average": sum(scores) / len(scores),
                    "count": len(scores),
                    "min": min(scores),
                    "max": max(scores),
                }
            else:
                results[opt] = {"total": 0, "average": 0, "count": 0}

        winner = max(results.items(), key=lambda x: x[1]["average"])
        threshold = (self.max_score - self.min_score) / 2

        if winner[1]["average"] >= threshold:
            dec = "adopted"
            rat = f"选项 {winner[0]} 最高平均分：{winner[1]['average']:.1f}"
        else:
            dec = "no_consensus"
            rat = f"最高分 {winner[1]['average']:.1f} 未达阈值 {threshold}"

        return {"decision": dec,
                "winner": winner[0] if dec == "adopted" else None,
                "results": results, "threshold": threshold,
                "rationale": rat}
