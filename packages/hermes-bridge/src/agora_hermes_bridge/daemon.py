"""Hermes Bridge daemon — manages multiple profile adapters.

Each profile gets its own HermesAdapter (AbstractBridge impl)
connected to Agora via AgoraAgentClient.
"""

from __future__ import annotations

import asyncio
import logging

from agora_agent_sdk import AgoraAgentClient
from agora_agent_sdk.protocol import TaskNode

from .adapter import HermesAdapter
from .config import BridgeConfig, ProfileConfig

logger = logging.getLogger(__name__)


class HermesBridgeDaemon:
    """Main daemon managing multiple Hermes profile bridges."""

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.adapters: dict[str, HermesAdapter] = {}
        self._running = False

    async def start(self) -> None:
        """Start the bridge daemon."""
        logger.info(
            "Starting Hermes Bridge for %d profiles",
            len(self.config.profiles),
        )
        self._running = True
        for profile in self.config.profiles:
            await self._register_profile(profile)
        await self._run_loop()

    async def _register_profile(self, profile: ProfileConfig) -> None:
        """Register a Hermes profile as an Agora agent."""
        agent_id = self.config.resolve_agent_id(profile)
        from agora_agent_sdk.client import AgentConnectionConfig
        cfg = AgentConnectionConfig(
            coordinator_url=self.config.coordinator_url,
            agent_id=agent_id,
            agent_name=f"Hermes-{profile.name}",
            agent_type="hermes",
            capabilities=profile.capabilities,
            model=profile.model,
            agent_token=profile.token or None,
        )
        client = AgoraAgentClient(cfg)
        adapter = HermesAdapter(client, profile.name)
        self.adapters[agent_id] = adapter
        logger.info("Registered profile %s as agent %s", profile.name, agent_id)

    async def _run_loop(self) -> None:
        """Main event loop: keep alive, delegate to adapters."""
        while self._running:
            await asyncio.sleep(self.config.poll_interval)
            logger.debug("Hermes Bridge heartbeat...")

    async def stop(self) -> None:
        """Stop the daemon gracefully."""
        logger.info("Stopping Hermes Bridge daemon")
        self._running = False
