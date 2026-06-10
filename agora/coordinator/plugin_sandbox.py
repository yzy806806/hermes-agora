"""Plugin sandbox: import blocking, timeout enforcement, and memory limits.

Provides safety boundaries for plugins running in the coordinator process.
Phase 10 uses advisory restrictions (no subprocess isolation).
"""
from __future__ import annotations

import asyncio
import logging
import tracemalloc
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from agora.coordinator.plugin import AgoraPlugin

logger = logging.getLogger(__name__)

DEFAULT_BLOCKED_IMPORTS = {"os", "subprocess", "socket", "ctypes"}
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY_LIMIT_MB = 100


class PluginSandbox:
    """Resource limits and safety boundaries for a single plugin."""

    def __init__(
        self,
        plugin: AgoraPlugin,
        blocked_imports: set[str] | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    ) -> None:
        self.plugin = plugin
        self.blocked_imports: set[str] = blocked_imports or set(
            DEFAULT_BLOCKED_IMPORTS
        )
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self._memory_exceeded = False

    def check_import(self, module_name: str) -> bool:
        """Return False if the import is blocked."""
        top_level = module_name.split(".")[0]
        if top_level in self.blocked_imports:
            logger.warning(
                "Plugin %r blocked from importing %r",
                self.plugin.manifest.name,
                module_name,
            )
            return False
        return True

    async def enforce_timeout(
        self, coro: Any, timeout: int | None = None
    ) -> Any:
        """Run a coroutine with a timeout; raise on violation."""
        secs = timeout or self.timeout_seconds
        return await asyncio.wait_for(coro, timeout=secs)

    def set_memory_limit(self, limit_mb: int) -> None:
        """Set advisory memory limit (checked after execution)."""
        self.memory_limit_mb = limit_mb

    def check_memory(self) -> bool:
        """Check if memory usage exceeds the limit. Advisory only."""
        if not tracemalloc.is_tracing():
            return True
        current_mb = tracemalloc.get_traced_memory()[0] / (1024 * 1024)
        if current_mb > self.memory_limit_mb:
            logger.warning(
                "Plugin %r exceeded memory limit: %.1fMB > %dMB",
                self.plugin.manifest.name,
                current_mb,
                self.memory_limit_mb,
            )
            self._memory_exceeded = True
            return False
        return True

    @property
    def memory_exceeded(self) -> bool:
        """Whether the memory limit was exceeded since last check."""
        return self._memory_exceeded


@asynccontextmanager
async def sandbox_context(
    sandbox: PluginSandbox,
) -> AsyncGenerator[PluginSandbox, None]:
    """Context manager wrapping plugin execution with safety checks."""
    tracemalloc_was_running = tracemalloc.is_tracing()
    if not tracemalloc_was_running:
        tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    try:
        yield sandbox
    finally:
        if not tracemalloc_was_running:
            tracemalloc.stop()
        else:
            snapshot_after = tracemalloc.take_snapshot()
            stats = snapshot_after.compare_to(snapshot_before, "lineno")
            total_kb = sum(s.size for s in stats) / 1024
            if total_kb > sandbox.memory_limit_mb * 1024:
                logger.warning(
                    "Plugin %r used %.0fKB exceeding %dMB limit",
                    sandbox.plugin.manifest.name,
                    total_kb,
                    sandbox.memory_limit_mb,
                )
