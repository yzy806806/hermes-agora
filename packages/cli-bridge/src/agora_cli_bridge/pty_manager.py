"""PTY subprocess manager for CLI Bridge.

Manages multiple named PTY subprocess instances. Each agent gets a unique
name and is tracked for lifecycle control.
"""
from __future__ import annotations

import asyncio
import logging
import os

from .pty_process import PtyProcess

logger = logging.getLogger(__name__)


class PtyManager:
    """Manages multiple CLI agents as named PTY subprocesses.

    Usage::

        mgr = PtyManager()
        proc = await mgr.spawn_agent("agent-1", ["codex", "chat"])
        output = await proc.read_output()
        await proc.write_input("hello\\n")
        await mgr.terminate("agent-1")
    """

    def __init__(self) -> None:
        self._agents: dict[str, PtyProcess] = {}

    def get(self, name: str) -> PtyProcess | None:
        """Get a spawned process by name, or None if not found."""
        return self._agents.get(name)

    async def spawn_agent(self, name: str, command: list[str]) -> PtyProcess:
        """Spawn a new agent with the given name and command.

        Args:
            name: Unique identifier for this agent.
            command: Command and arguments to execute.

        Returns:
            The spawned PtyProcess instance.

        Raises:
            ValueError: If an agent with this name already exists.
        """
        if name in self._agents:
            raise ValueError(f"Agent '{name}' already spawned")

        master_fd, slave_fd = os.openpty()
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
        )
        os.close(slave_fd)

        pty_proc = PtyProcess(proc.pid, master_fd)
        self._agents[name] = pty_proc
        logger.info("Spawned agent '%s' (pid=%s)", name, proc.pid)
        return pty_proc

    async def terminate(self, name: str) -> None:
        """Terminate and remove an agent by name."""
        proc = self._agents.pop(name, None)
        if proc is None:
            return
        await proc.terminate()
        proc.close()
        logger.info("Terminated agent '%s'", name)

    async def terminate_all(self) -> None:
        """Terminate all managed agents."""
        for name in list(self._agents.keys()):
            await self.terminate(name)
