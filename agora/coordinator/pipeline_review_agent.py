"""Pipeline review agent lookup helpers (Phase 13.1c).

Extracted from pipeline_review.py to keep files under 80 lines.
Handles both sync and async get_online_agents() return types.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def await_online_agents(hub: Any) -> list[str]:
    """Resolve online agents from hub, handling sync/async return types."""
    online = hub.get_online_agents()
    # Coroutine (e.g. async def or AsyncMock) — await first
    if asyncio.iscoroutine(online):
        online = await online
    if isinstance(online, list):
        return online
    # Async iterable — collect all items
    result: list[str] = []
    async for aid in online:
        result.append(aid)
    return result


def get_agent_capabilities(hub: Any, agent_id: str) -> list[str]:
    """Extract capabilities from agent metadata if available."""
    app_state = getattr(hub, "_app_state", None)
    if app_state is None:
        return []
    registry = getattr(app_state, "agent_registry", None)
    if registry is None:
        return []
    info = registry.get(agent_id)
    if info is None:
        return []
    return info.get("capabilities", [])


async def find_review_agent(hub: Any) -> Optional[str]:
    """Find an online agent with code-review capability.

    Checks agent metadata for 'code-review' in capabilities,
    then falls back to name-based heuristic.
    """
    agents = await await_online_agents(hub)
    for aid in agents:
        caps = get_agent_capabilities(hub, aid)
        if "code-review" in caps:
            return aid
    # Fallback: name-based heuristic
    for aid in agents:
        if "review" in aid.lower():
            return aid
    return None
