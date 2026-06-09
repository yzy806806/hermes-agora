"""WebSocket connection pool for the Agora agent client.

Manages a persistent WebSocket connection with auto-reconnect.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets

from .config import AgoraConfig

logger = logging.getLogger(__name__)


class WSConnection:
    """Persistent WebSocket connection with reconnect logic."""

    def __init__(self, config: AgoraConfig) -> None:
        self._config = config
        self._ws: Any = None
        self._lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Open or reopen the WebSocket connection. Returns True on success."""
        try:
            self._ws = await websockets.connect(
                self._config.ws_endpoint,
                open_timeout=self._config.connect_timeout,
            )
            logger.info("WS connected to %s", self._config.ws_endpoint)
            return True
        except Exception as exc:
            logger.warning("WS connect failed: %s", exc)
            self._ws = None
            return False

    async def ensure_connected(self) -> bool:
        """Ensure WS is open, reconnecting up to max_retry times."""
        if self._ws is not None and self._ws.open:
            return True
        async with self._lock:
            # Re-check after acquiring lock
            if self._ws is not None and self._ws.open:
                return True
            for attempt in range(self._config.max_retry):
                if await self.connect():
                    return True
                await asyncio.sleep(0.5 * (attempt + 1))
            return False

    async def send_and_wait(
        self, message: dict[str, Any], timeout: float = 30.0
    ) -> dict[str, Any] | None:
        """Send a WS message and wait for a response of matching type."""
        if not await self.ensure_connected():
            return None
        assert self._ws is not None
        msg_type = message.get("type", "")
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[msg_type] = fut
        try:
            await self._ws.send(json.dumps(message))
            # Read responses until we find a match or timeout
            async with asyncio.timeout(timeout):
                while not fut.done():
                    raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
                    resp = json.loads(raw)
                    resp_type = resp.get("type", "")
                    if resp_type in self._pending and not self._pending[resp_type].done():
                        self._pending[resp_type].set_result(resp)
                    elif resp_type == "ERROR":
                        return resp
            return fut.result()
        except Exception as exc:
            logger.warning("WS send_and_wait failed: %s", exc)
            self._ws = None
            return None
        finally:
            self._pending.pop(msg_type, None)

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
