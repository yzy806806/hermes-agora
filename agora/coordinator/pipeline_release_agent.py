"""Pipeline release agent lookup helpers (Phase 13.1d).

Mirrors pipeline_review_agent.py pattern: capability-based
lookup with name-based fallback for the releaser agent.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from agora.coordinator.pipeline_review_agent import (
    await_online_agents, get_agent_capabilities,
)

logger = logging.getLogger(__name__)


async def find_release_agent(hub: Any) -> Optional[str]:
    """Find an online agent with release capability.

    Checks agent metadata for 'release' in capabilities,
    then falls back to name-based heuristic.
    """
    agents = await await_online_agents(hub)
    for aid in agents:
        caps = get_agent_capabilities(hub, aid)
        if "release" in caps:
            return aid
    # Fallback: name-based heuristic
    for aid in agents:
        if "releaser" in aid.lower() or "release" in aid.lower():
            return aid
    return None
