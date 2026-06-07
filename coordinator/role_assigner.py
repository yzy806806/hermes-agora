"""Model-aware role assignment and perspective diversity (Phase 6.5).

Assigns discussion roles based on model capabilities and ensures
perspective diversity in discussions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .model_capabilities import ModelCapability, ModelProfiler
from .models import DiscussionRole

if TYPE_CHECKING:
    from coordinator.storage.storage import Storage

logger = logging.getLogger(__name__)

# Role instruction templates for each DiscussionRole
ROLE_INSTRUCTIONS: dict[DiscussionRole, str] = {
    DiscussionRole.FACT_CHECKER: "请核查各方发言的事实准确性，指出任何不准确之处。",
    DiscussionRole.CREATIVE: "请从非常规角度思考，提出创新性的观点和解决方案。",
    DiscussionRole.EXPERT: "请运用专业知识，提供深度分析和技术见解。",
    DiscussionRole.NEUTRAL: "请保持客观，总结各方观点，促进共识形成。",
    DiscussionRole.SUPPORT_ADVOCATE: "请从支持角度阐述理由，提供有力论据。",
    DiscussionRole.OPPOSE_ADVOCATE: "请从反对角度阐述理由，提出合理质疑。",
}


class ModelAwareRoleAssigner:
    """Assigns discussion roles based on model capabilities."""

    def __init__(self, storage: Storage, profiler: ModelProfiler) -> None:
        self.storage = storage
        self.profiler = profiler

    async def assign_optimal_roles(self, motion_id: str) -> dict[str, DiscussionRole]:
        """Assign optimal discussion roles to each agent based on model capabilities."""
        agents = await self.storage.list_agents()
        assignments: dict[str, DiscussionRole] = {}

        by_cap: dict[ModelCapability, list[dict]] = {
            ModelCapability.FACTUAL: [],
            ModelCapability.CREATIVE: [],
            ModelCapability.ANALYTICAL: [],
            ModelCapability.REASONING_STRONG: [],
        }

        for agent in agents:
            profile = self.profiler.get_profile(agent.get("model", ""))
            for cap in by_cap:
                if cap in profile.capabilities:
                    by_cap[cap].append(agent)

        # Assign specialized roles based on strongest capability
        if by_cap[ModelCapability.FACTUAL]:
            a = by_cap[ModelCapability.FACTUAL][0]
            assignments[a["agent_id"]] = DiscussionRole.FACT_CHECKER

        if by_cap[ModelCapability.CREATIVE]:
            a = by_cap[ModelCapability.CREATIVE][0]
            if a["agent_id"] not in assignments:
                assignments[a["agent_id"]] = DiscussionRole.CREATIVE

        if by_cap[ModelCapability.ANALYTICAL]:
            a = by_cap[ModelCapability.ANALYTICAL][0]
            if a["agent_id"] not in assignments:
                assignments[a["agent_id"]] = DiscussionRole.EXPERT

        # Remaining agents get NEUTRAL role
        assigned = set(assignments.keys())
        for agent in agents:
            if agent["agent_id"] not in assigned:
                assignments[agent["agent_id"]] = DiscussionRole.NEUTRAL

        logger.info("Assigned roles for motion %s: %s", motion_id, assignments)
        return assignments

    @staticmethod
    def get_role_instruction(role: DiscussionRole) -> str:
        """Get instruction text for a discussion role."""
        return ROLE_INSTRUCTIONS.get(role, "请积极参与讨论。")
