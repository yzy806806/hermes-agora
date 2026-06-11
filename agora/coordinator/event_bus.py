"""Event bus bridge — Phase 11.5a.

Connects the coordinator's event system to the dashboard
WebSocket hub for real-time push notifications.

Hooks into the existing ConnectionManager.broadcast() flow
to also forward events to dashboard clients.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .dashboard_ws import DashboardHub

logger = logging.getLogger(__name__)

_dashboard_hub: Optional[DashboardHub] = None


def init_event_bus(hub: DashboardHub) -> None:
    """Set the dashboard hub reference for event forwarding."""
    global _dashboard_hub
    _dashboard_hub = hub


async def publish(
    event_type: str, payload: dict[str, Any],
    channel: str = "events",
) -> int:
    """Forward an event to all subscribed dashboard clients.

    Returns the number of clients that received the event.
    If dashboard hub is not initialized, returns 0 silently.
    """
    if _dashboard_hub is None:
        return 0
    return await _dashboard_hub.broadcast_event(event_type, payload, channel)
