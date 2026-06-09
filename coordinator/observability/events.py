"""Structured event logging for Agora Coordinator.

Defines EventType enum, Event dataclass, and EventEmitter
that outputs JSON Lines to stdout and pushes via WebSocket.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """All structured event types in the system."""
    # Discussion lifecycle
    MOTION_CREATED = "motion.created"
    MOTION_STARTED = "motion.started"
    MOTION_ASSESSING = "motion.assessing"
    MOTION_VOTING_STARTED = "motion.voting_started"
    MOTION_CLOSED = "motion.closed"
    # Agent lifecycle
    AGENT_REGISTERED = "agent.registered"
    AGENT_DISCONNECTED = "agent.disconnected"
    AGENT_TIMEOUT = "agent.timeout"
    # Discussion process
    SPEAK = "speak"
    QUALITY_THRESHOLD_MET = "quality.threshold_met"
    QUALITY_INTERVENTION = "quality.intervention"
    CONSENSUS_JUMP = "consensus.jump"
    DEVILS_ADVOCATE_TRIGGERED = "devils_advocate.triggered"
    # Voting
    VOTE_CAST = "vote.cast"
    VOTE_RESULT = "vote.result"
    # System
    HEARTBEAT_LOST = "heartbeat.lost"
    DEADLOCK_DETECTED = "deadlock.detected"
    MEMORY_SYNC = "memory.sync"


@dataclass
class Event:
    """A single structured event."""
    type: EventType
    motion_id: str
    timestamp: datetime
    agent_id: Optional[str]
    data: dict
    trace_id: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        d["timestamp"] = self.timestamp.isoformat()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventEmitter:
    """Emit events to stdout (JSON Lines) and WebSocket."""

    def __init__(self, ws_manager=None) -> None:
        self._ws = ws_manager
        self._subscribers: list = []

    def subscribe(self, callback) -> None:
        self._subscribers.append(callback)

    async def emit(self, event: Event) -> None:
        """Emit event: log as JSON Line + push via WS."""
        line = event.to_json()
        logger.info("EVENT %s", line)
        # WS push to motion-specific events channel
        if self._ws is not None:
            channel = f"discussions:{event.motion_id}:events"
            await self._ws.broadcast({
                "type": "EVENT",
                "channel": channel,
                "payload": event.to_dict(),
            })
        for cb in self._subscribers:
            cb(event)
