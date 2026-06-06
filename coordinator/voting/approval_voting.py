"""Approval voting — each voter approves zero or more options."""

from __future__ import annotations

from typing import Dict, List


class ApprovalVoting:
    """Tally where voters can approve multiple options; most approvals wins."""

    def count(self, votes: List[dict]) -> dict:
        """Count approval votes. Each vote: {approved: [opt1, opt2, ...]}."""
        if not votes:
            return {"decision": "no_consensus", "rationale": "无投票"}

        # Collect all options
        all_opts: set[str] = set()
        for v in votes:
            all_opts.update(v.get("approved", []))

        if not all_opts:
            return {"decision": "no_consensus", "rationale": "无有效投票"}

        # Count approvals per option
        counts: Dict[str, int] = {o: 0 for o in all_opts}
        for v in votes:
            for opt in v.get("approved", []):
                if opt in counts:
                    counts[opt] += 1

        total_voters = len(votes)
        winner = max(counts.items(), key=lambda x: x[1])

        if winner[1] > total_voters / 2:
            dec = "adopted"
            rat = f"{winner[0]} 获得认可票最多：{winner[1]}/{total_voters}"
        else:
            dec = "no_consensus"
            rat = f"最高票 {winner[0]} 未过半数"

        return {
            "decision": dec,
            "winner": winner[0] if dec == "adopted" else None,
            "results": counts,
            "total_voters": total_voters,
            "rationale": rat,
        }
