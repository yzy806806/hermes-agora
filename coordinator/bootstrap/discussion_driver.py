"""Discussion Driver — drive Agora discussions for bootstrap decisions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class DiscussionConfig:
    """Configuration for a bootstrap discussion."""
    motion_title: str
    motion_description: str
    participants: list[str] = field(default_factory=list)
    voting_method: str = "ranked_choice"
    auto_approve_threshold: float = 0.8
    max_rounds: int = 5


@dataclass
class DiscussionResult:
    """Result of a completed discussion."""
    motion_id: str
    decision: str  # adopted / rejected / no_consensus
    recommended_actions: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    rationale: str = ""
    risk_assessment: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class DiscussionDriver:
    """Drive Agora discussions for development direction decisions."""

    def __init__(self, coordinator_url: str) -> None:
        self.coordinator_url = coordinator_url.rstrip("/")

    async def start_dev_discussion(
        self, config: DiscussionConfig,
    ) -> str:
        """Start a development discussion. Returns the motion_id."""
        motion_id = await self._create_motion(
            title=config.motion_title,
            description=config.motion_description,
            voting_method=config.voting_method,
        )
        for agent_id in config.participants:
            await self._register_participant(motion_id, agent_id)
        await self._start_discussion(motion_id, config.max_rounds)
        logger.info("Started discussion %s on '%s'", motion_id, config.motion_title)
        return motion_id

    async def _create_motion(
        self, title: str, description: str, voting_method: str,
    ) -> str:
        """Create a motion via the coordinator API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.coordinator_url}/api/v1/motions",
                    json={
                        "title": title,
                        "description": description,
                        "voting_method": voting_method,
                        "context": "auto_bootstrap",
                    },
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data["id"]
        except aiohttp.ClientError as exc:
            logger.error("Failed to create motion: %s", exc)
            raise RuntimeError(f"Motion creation failed: {exc}") from exc

    async def _register_participant(
        self, motion_id: str, agent_id: str,
    ) -> None:
        """Register a participant via the coordinator API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.coordinator_url}/api/v1/agents/register",
                    json={
                        "agent_id": agent_id,
                        "name": agent_id,
                        "role": "expert",
                    },
                ) as resp:
                    if resp.status not in (200, 201, 409):
                        logger.warning(
                            "Register participant %s returned %s",
                            agent_id, resp.status,
                        )
        except aiohttp.ClientError as exc:
            logger.warning("Failed to register participant %s: %s", agent_id, exc)

    async def _start_discussion(
        self, motion_id: str, max_rounds: int,
    ) -> None:
        """Trigger discussion start via the coordinator API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.coordinator_url}/api/v1/motions/{motion_id}/start",
                ) as resp:
                    if resp.status not in (200, 201):
                        logger.warning(
                            "Start discussion %s returned %s",
                            motion_id, resp.status,
                        )
        except aiohttp.ClientError as exc:
            logger.warning("Failed to start discussion %s: %s", motion_id, exc)

    async def wait_for_result(
        self, motion_id: str, timeout: int = 3600,
    ) -> DiscussionResult:
        """Poll until the discussion closes or timeout."""
        start = datetime.utcnow()
        while (datetime.utcnow() - start).seconds < timeout:
            result = await self._check_motion_status(motion_id)
            if result is not None:
                return result
            await asyncio.sleep(10)
        raise TimeoutError(f"Discussion {motion_id} timed out after {timeout}s")

    async def _check_motion_status(
        self, motion_id: str,
    ) -> Optional[DiscussionResult]:
        """Check if a motion is closed and return its result."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.coordinator_url}/api/v1/motions/{motion_id}",
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    if data.get("status") != "closed":
                        return None
                    return DiscussionResult(
                        motion_id=motion_id,
                        decision=data.get("decision", "no_consensus"),
                        recommended_actions=data.get("action_items", []),
                        confidence=data.get("confidence", 0.0),
                        rationale=data.get("rationale", ""),
                        risk_assessment=data.get("risk_assessment", {}),
                    )
        except aiohttp.ClientError as exc:
            logger.warning("Status check failed for %s: %s", motion_id, exc)
            return None

    async def cancel_discussion(self, motion_id: str) -> bool:
        """Attempt to cancel an ongoing discussion."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.coordinator_url}/api/v1/motions/{motion_id}",
                ) as resp:
                    return resp.status in (200, 204)
        except aiohttp.ClientError as exc:
            logger.error("Cancel failed for %s: %s", motion_id, exc)
            return False
