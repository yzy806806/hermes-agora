"""Model capability profiling for multi-model diversity (Phase 6.5).

Provides capability flags, model profiles, and profiling utilities
to enable model-aware role assignment in discussions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Flag
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from coordinator.storage.storage import Storage


class ModelCapability(Flag):
    """Model capability flags for role assignment."""

    REASONING_STRONG = 1 << 0
    CREATIVE = 1 << 1
    FACTUAL = 1 << 2
    ANALYTICAL = 1 << 3
    DOMAIN_EXPERT = 1 << 4


@dataclass
class ModelProfile:
    """Model capability profile."""

    model_name: str
    capabilities: ModelCapability
    preferred_stance: str | None = None
    weaknesses: list[str] = field(default_factory=list)


# Preset model profiles for common models
MODEL_PROFILES: dict[str, ModelProfile] = {
    "gpt-4": ModelProfile(
        model_name="gpt-4",
        capabilities=ModelCapability.REASONING_STRONG | ModelCapability.ANALYTICAL,
        weaknesses=["may be overly cautious"],
    ),
    "gpt-4o": ModelProfile(
        model_name="gpt-4o",
        capabilities=ModelCapability.REASONING_STRONG | ModelCapability.ANALYTICAL,
        weaknesses=["may be overly cautious"],
    ),
    "claude-3": ModelProfile(
        model_name="claude-3",
        capabilities=ModelCapability.CREATIVE | ModelCapability.FACTUAL,
        preferred_stance="neutral",
    ),
    "claude-3-opus": ModelProfile(
        model_name="claude-3-opus",
        capabilities=ModelCapability.CREATIVE | ModelCapability.FACTUAL,
        preferred_stance="neutral",
    ),
    "claude-3-sonnet": ModelProfile(
        model_name="claude-3-sonnet",
        capabilities=ModelCapability.CREATIVE | ModelCapability.FACTUAL,
        preferred_stance="neutral",
    ),
    "gemini": ModelProfile(
        model_name="gemini",
        capabilities=ModelCapability.REASONING_STRONG | ModelCapability.DOMAIN_EXPERT,
        weaknesses=["may be too technical"],
    ),
    "gemini-pro": ModelProfile(
        model_name="gemini-pro",
        capabilities=ModelCapability.REASONING_STRONG | ModelCapability.DOMAIN_EXPERT,
        weaknesses=["may be too technical"],
    ),
}


class ModelProfiler:
    """Model capability analyzer."""

    def get_profile(self, model_name: str) -> ModelProfile:
        """Get model profile by name, returning default if unknown."""
        normalized = model_name.lower() if model_name else "unknown"
        return MODEL_PROFILES.get(
            normalized,
            ModelProfile(model_name=model_name or "unknown", capabilities=ModelCapability(0)),
        )

    async def infer_capabilities(self, agent_id: str, storage: Storage) -> ModelProfile:
        """Infer model capabilities from agent's historical messages."""
        agent = await storage.get_agent(agent_id)
        if agent and agent.get("model"):
            return self.get_profile(agent["model"])
        return ModelProfile(model_name="unknown", capabilities=ModelCapability(0))
