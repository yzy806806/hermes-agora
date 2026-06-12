"""PTY subprocess manager for CLI-based agents.

Manages named PTY subprocess instances. Each agent gets a unique
name and is tracked by PtyManager for lifecycle control.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)


class PtyProcess:
    """Wraps a single PTY subprocess with non-blocking I/O."""

    def __init__(self, pid: int, master_fd: int) -> None:
        self.pid = pid
        self._master_fd = master_fd

    def is_alive(self) -> bool:
        """Check if the subprocess is still running."""
        try:
            pid, _ = os.waitpid(self.pid, os.WNOHANG)
            return pid == 0
        except ChildProcessError:
            return False

    async def read_output(self, size: int = 4096) -> str:
        """Non-blocking read from PTY, returns decoded string."""
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None, os.read, self._master_fd, size,
            )
            return data.decode("utf-8", errors="replace")
        except OSError:
            return ""

    async def write_input(self, data: str) -> None:
        """Write string to subprocess stdin via PTY."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, os.write, self._master_fd, data.encode("utf-8"),
        )

    async def terminate(self, timeout: float = 5.0) -> None:
        """Graceful terminate: SIGTERM then SIGKILL."""
        if not self.is_alive():
            return
        try:
            os.kill(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        for _ in range(int(timeout * 10)):
            if not self.is_alive():
                return
            await asyncio.sleep(0.1)
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def close(self) -> None:
        """Close the master FD."""
        try:
            os.close(self._master_fd)
        except OSError:
            pass
