"""Heartbeat monitoring for agent connections (PING/PONG protocol)."""
from __future__ import annotations
import asyncio
import logging
import time
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ws import ConnectionManager

logger = logging.getLogger(__name__)

class AgentConnectionStatus(str, Enum):
    """Agent connection health status."""
    ACTIVE = "active"
    UNRESPONSIVE = "unresponsive"
    OFFLINE = "offline"

class HeartbeatManager:
    """Manages periodic heartbeat PING/PONG for agent connections."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        self._mgr = connection_manager
        self.pending_pings: dict[str, float] = {}
        self.missed_pings: dict[str, int] = {}
        self._task: asyncio.Task | None = None

    async def start_heartbeat(self, interval: int = 30) -> None:
        """Start periodic heartbeat task (default 30s)."""
        self._task = asyncio.create_task(self._heartbeat_loop(interval))
        logger.info("Heartbeat started with %ds interval", interval)

    async def _heartbeat_loop(self, interval: int) -> None:
        while True:
            await asyncio.sleep(interval)
            await self._send_heartbeats()

    async def _send_heartbeats(self) -> None:
        """Send PING to all connected agents."""
        for agent_id in list(self._mgr.active_connections.keys()):
            try:
                await self._mgr.send(agent_id, {
                    "type": "PING", "timestamp": time.time(),
                })
                self.pending_pings[agent_id] = time.time()
            except Exception:
                logger.warning("PING failed for agent %s", agent_id)

    def handle_pong(self, agent_id: str) -> None:
        """Process PONG — clear pending ping, reset miss count."""
        self.pending_pings.pop(agent_id, None)
        self.missed_pings[agent_id] = 0
        logger.debug("PONG received from %s", agent_id)

    def mark_offline(self, agent_id: str) -> None:
        """Mark agent OFFLINE after 3 missed PONGs."""
        self.pending_pings.pop(agent_id, None)
        self.missed_pings[agent_id] = 3
        logger.warning("Agent %s marked OFFLINE", agent_id)

    def get_connection_status(self, agent_id: str) -> AgentConnectionStatus:
        """Return ACTIVE / UNRESPONSIVE / OFFLINE for the agent."""
        missed = self.missed_pings.get(agent_id, 0)
        if missed >= 3:
            return AgentConnectionStatus.OFFLINE
        if missed >= 1:
            return AgentConnectionStatus.UNRESPONSIVE
        return AgentConnectionStatus.ACTIVE

    async def stop(self) -> None:
        """Cancel the heartbeat background task."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Heartbeat stopped")
