"""Weighted voting — agents have different vote weights."""

from __future__ import annotations

from typing import Dict, List

from coordinator.voting.weighted_types import WeightedVoteResult


class WeightedVoting:
    """Calculate weighted vote results with confidence adjustment."""

    def __init__(self, weights: Dict[str, float], threshold: float = 0.5):
        self.weights = weights
        self.threshold = threshold

    def count(self, votes: List[dict]) -> WeightedVoteResult:
        """Tally weighted votes. Each vote: {agent_id, vote, confidence?}."""
        w_yes = w_no = w_abstain = 0.0

        for v in votes:
            weight = self.weights.get(v["agent_id"], 1.0)
            confidence = v.get("confidence", 1.0)
            effective = weight * confidence
            choice = v["vote"]

            if choice == "yes":
                w_yes += effective
            elif choice == "no":
                w_no += effective
            else:
                w_abstain += effective

        total = w_yes + w_no
        if total == 0:
            return WeightedVoteResult(decision="no_consensus",
                                      rationale="无有效投票",
                                      threshold=self.threshold)

        eff_yes = w_yes / total
        if eff_yes >= self.threshold:
            dec = "adopted"
            rat = f"加权多数通过：{w_yes:.1f} 赞成 (有效比例 {eff_yes:.1%})"
        else:
            dec = "rejected"
            rat = f"提案被否决：{w_no:.1f} 反对"

        return WeightedVoteResult(
            decision=dec,
            total_weight_yes=w_yes,
            total_weight_no=w_no,
            total_weight_abstain=w_abstain,
            effective_yes=eff_yes,
            effective_no=1 - eff_yes,
            threshold=self.threshold,
            rationale=rat,
        )
