"""Advanced voting manager for the Agora Coordinator.

Orchestrates vote handling, validation, counting, and result
broadcasting across all supported voting methods.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ..models import MotionStatus, VotingMethod
from .factory import VoteCounterFactory
from .weight_manager import WeightManager

if TYPE_CHECKING:
    from ..storage import Storage
    from ..ws import ConnectionManager

logger = logging.getLogger(__name__)

# Binary voting methods that expect type=binary + vote field
_BINARY_METHODS = {
    VotingMethod.SIMPLE_MAJORITY, VotingMethod.SUPERMAJORITY,
    VotingMethod.UNANIMOUS, VotingMethod.WEIGHTED,
}


class AdvancedVotingManager:
    """High-level voting manager with multi-method support.

    Delegates counting to VoteCounterFactory and weight resolution
    to WeightManager. Handles vote validation, storage, and
    result broadcasting.
    """

    def __init__(
        self,
        storage: Storage,
        ws_manager: ConnectionManager,
        config: dict,
    ) -> None:
        self.storage = storage
        self.ws_manager = ws_manager
        self.weight_manager = WeightManager(storage, config)

    async def handle_vote(
        self, agent_id: str, motion_id: str, vote_data: dict
    ) -> None:
        """Validate, store, and confirm a vote."""
        motion = await self.storage.get_motion(motion_id)
        if not motion or motion["status"] != MotionStatus.VOTING:
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "INVALID_STATE",
                            "message": "Not in voting phase"},
            })
            return

        if not self._validate_vote_format(
            motion["voting_method"], vote_data
        ):
            await self.ws_manager.send(agent_id, {
                "type": "ERROR",
                "payload": {"code": "INVALID_VOTE_FORMAT",
                            "message": "Vote format mismatch"},
            })
            return

        vote_type = vote_data.get("type", "binary")
        await self.storage.add_vote(
            motion_id=motion_id,
            agent_id=agent_id,
            vote=vote_data.get("vote", "abstain"),
            confidence=vote_data.get("confidence", 1.0),
            reason=vote_data.get("reason"),
            vote_type=vote_type,
            vote_data=json.dumps(vote_data),
        )
        await self.ws_manager.send(agent_id, {
            "type": "VOTE_CONFIRMED",
            "motion_id": motion_id,
            "payload": {"vote": vote_data.get("vote")},
        })

    def _validate_vote_format(
        self, method: str, vote_data: dict
    ) -> bool:
        """Check that vote payload matches the expected method format."""
        vtype = vote_data.get("type", "binary")
        try:
            vm = VotingMethod(method)
        except ValueError:
            return True
        if vm in _BINARY_METHODS:
            return vtype == "binary" and "vote" in vote_data
        if vm in (VotingMethod.RANKED_CHOICE, VotingMethod.BORDA_COUNT):
            return vtype == "ranking" and "ranking" in vote_data
        return True

    async def close_voting(self, motion_id: str) -> dict[str, Any]:
        """Close voting, count results, and broadcast."""
        motion = await self.storage.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")

        votes = await self.storage.get_votes(motion_id)
        method_str = motion["voting_method"]
        vm = VotingMethod(method_str)

        if vm == VotingMethod.WEIGHTED:
            result = await self._count_weighted(motion_id, votes)
        else:
            counter = VoteCounterFactory.get_counter(vm)
            result = counter.count(votes)

        await self.storage.update_motion_status(
            motion_id, MotionStatus.CLOSED,
            decision=result.get("decision", "no_consensus"),
            rationale=result.get("rationale", ""),
        )
        await self.ws_manager.broadcast({
            "type": "RESULT",
            "motion_id": motion_id,
            "payload": {
                "decision": result.get("decision"),
                "voting_method": method_str,
                "results": result,
                "rationale": result.get("rationale"),
            },
        })
        return result

    async def _count_weighted(
        self, motion_id: str, votes: list[dict]
    ) -> dict[str, Any]:
        """Count weighted votes using WeightManager for weights."""
        weights = await self.weight_manager.get_weights(motion_id)
        yes_w = no_w = abstain_w = 0.0
        for v in votes:
            w = weights.get(v.get("agent_id", ""), 1.0)
            conf = v.get("confidence", 1.0)
            ew = w * conf
            choice = v.get("vote", "abstain")
            if choice == "yes":
                yes_w += ew
            elif choice == "no":
                no_w += ew
            else:
                abstain_w += ew
        total = yes_w + no_w
        if total == 0:
            return {"decision": "no_consensus", "rationale": "No votes"}
        ratio = yes_w / total
        if ratio >= 0.5:
            return {"decision": "adopted",
                    "rationale": f"Weighted majority: {ratio:.0%}"}
        return {"decision": "rejected",
                "rationale": f"Below threshold: {ratio:.0%}"}
