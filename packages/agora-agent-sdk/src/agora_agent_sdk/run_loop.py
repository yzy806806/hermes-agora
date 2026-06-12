"""Run loop for AgoraAgentClient.

Receives WS messages and dispatches to bridge methods.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from .protocol import AgentConfig, MessageType, TaskNode

if TYPE_CHECKING:
    from .client import AgoraAgentClient

logger = logging.getLogger(__name__)


async def run(client: AgoraAgentClient) -> None:
    """Main event loop. Receives WS messages and dispatches to bridge."""
    if not client._connected or client._ws is None:
        raise RuntimeError("Not connected. Call connect() first.")
    if client._bridge is None:
        raise RuntimeError("No bridge set. Call set_bridge() first.")

    ws = client._ws
    bridge = client._bridge

    while client._connected:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
            msg = json.loads(raw) if isinstance(raw, str) else raw
            msg_type = msg.get("type")

            if msg_type == MessageType.TASK_ASSIGNED.value:
                payload = msg.get("payload", {})
                task = TaskNode(**payload)
                await bridge.on_task_assigned(task)

            elif msg_type == MessageType.SPEECH_ADDED.value:
                payload = msg.get("payload", {})
                await bridge.on_discussion_message(
                    payload.get("motion_id", ""),
                    payload.get("content", ""),
                )

            elif msg_type == MessageType.DEVILS_ADVOCATE_REQUEST.value:
                payload = msg.get("payload", {})
                response = await bridge.on_devils_advocate(
                    payload.get("motion_id", ""),
                    payload.get("topic", ""),
                )
                await ws.send(json.dumps({
                    "type": MessageType.DEVILS_ADVOCATE_RESPONSE.value,
                    "payload": {"content": response},
                }))

            elif msg_type == MessageType.HEARTBEAT_ACK.value:
                client._last_ack = time.time()

            elif msg_type == MessageType.WELCOME.value:
                payload = msg.get("payload", {})
                config_data = payload.get("config", {})
                client._agent_config = AgentConfig(**config_data)

            elif msg_type == MessageType.ERROR.value:
                logger.error("WS error: %s", msg.get("payload", {}))

        except asyncio.TimeoutError:
            continue
        except Exception as exc:
            logger.error("Run loop error: %s", exc)
            break
