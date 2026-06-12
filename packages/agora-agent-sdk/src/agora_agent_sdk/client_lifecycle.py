"""AgoraAgentClient — lifecycle methods: connect, disconnect, run, heartbeat.

Methods are designed to be bound onto the AgoraAgentClient class.
The run() loop delegates to run_loop.py for message dispatch.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import websockets

from .protocol import MessageType
from .run_loop import run as run_loop

logger = logging.getLogger(__name__)


async def connect(self: Any) -> None:
    """Open WS to coordinator and start heartbeat loop."""
    ws_url = self._config.ws_endpoint
    self._ws = await websockets.connect(ws_url, open_timeout=10)
    self._connected = True
    self._last_ack = time.monotonic()
    self._heartbeat_task = asyncio.create_task(
        _heartbeat_loop(self)
    )
    logger.info("WS connected to %s", ws_url)


async def disconnect(self: Any) -> None:
    """Close WS connection and cancel heartbeat."""
    self._connected = False
    if hasattr(self, "_heartbeat_task") and self._heartbeat_task:
        self._heartbeat_task.cancel()
    if self._ws is not None:
        await self._ws.close()
        self._ws = None
    await self._http.aclose()


async def run(self: Any) -> None:
    """Main event loop — receive WS, dispatch to bridge."""
    await run_loop(self)


async def _heartbeat_loop(self: Any) -> None:
    """Periodic heartbeat sender."""
    interval = self._config.heartbeat_interval
    while self._connected:
        try:
            from .client_ws import _send_ws
            await _send_ws(self, MessageType.HEARTBEAT, {})
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.warning("Heartbeat failed")
            break