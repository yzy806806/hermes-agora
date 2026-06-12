"""AgoraAgentClient — WS-based methods: speak, vote, task reporting.

Split from client.py to stay under 80 lines per file.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .protocol import MessageType

logger = logging.getLogger(__name__)


async def _send_ws(self: Any, msg_type: MessageType, payload: dict) -> None:
    """Send a WS message. Raises RuntimeError if not connected."""
    if not self._ws:
        raise RuntimeError("Not connected — call connect() first")
    msg = json.dumps({"type": msg_type.value, "payload": payload})
    await self._ws.send(msg)


async def speak(self: Any, motion_id: str, content: str) -> dict:
    """Send a speech in a discussion round via WS."""
    await _send_ws(
        self, MessageType.SPEAK,
        {"motion_id": motion_id, "content": content},
    )
    return {"success": True}


async def vote(self: Any, motion_id: str, choice: str) -> dict:
    """Cast a vote on a motion via WS."""
    await _send_ws(
        self, MessageType.VOTE,
        {"motion_id": motion_id, "vote": choice},
    )
    return {"success": True}


# -- Task Execution Reporting ----------------------------------------

async def report_task_start(self: Any, task_id: str) -> None:
    """Notify coordinator that task execution has begun."""
    await _send_ws(self, MessageType.TASK_STARTED, {"task_id": task_id})


async def report_task_progress(
    self: Any, task_id: str, progress: float
) -> None:
    """Report task progress (0.0 – 1.0)."""
    await _send_ws(
        self, MessageType.TASK_PROGRESS,
        {"task_id": task_id, "progress": progress},
    )


async def report_task_complete(
    self: Any, task_id: str, artifacts: list[str] | None = None
) -> None:
    """Notify coordinator that task finished successfully."""
    await _send_ws(
        self, MessageType.TASK_COMPLETED,
        {"task_id": task_id, "artifacts": artifacts or []},
    )


async def report_task_failed(
    self: Any, task_id: str, error: str = ""
) -> None:
    """Notify coordinator that task execution failed."""
    await _send_ws(
        self, MessageType.TASK_FAILED,
        {"task_id": task_id, "error": error},
    )
