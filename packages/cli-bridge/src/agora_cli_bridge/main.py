"""CLI Bridge main entry point.

Starts a CLI agent subprocess via PTY, connects to Agora
Coordinator via the Agent SDK, and routes tool calls between
the agent and Agora.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from typing import Optional

from agora_agent_sdk import AgoraAgentClient, AgentConnectionConfig

from .adapters import get_adapter, ToolResult
from .pty_manager import PtyManager

logger = logging.getLogger(__name__)


class CLIBridge:
    """Bridge connecting a CLI agent to Agora Coordinator.

    Lifecycle: start → read agent output → parse tool calls
               → execute/report → write results back → stop
    """

    def __init__(
        self,
        agent_type: str,
        command: list[str],
        coordinator_url: str = "http://localhost:8765",
        agent_id: str = "",
        agent_name: str = "",
        capabilities: list[str] | None = None,
        model: str = "unknown",
    ) -> None:
        self._adapter = get_adapter(agent_type)
        self._pty = PtyManager()
        self._command = command
        self._client = AgoraAgentClient(
            AgentConnectionConfig(
                coordinator_url=coordinator_url,
                agent_id=agent_id,
                agent_name=agent_name,
                agent_type="cli",
                capabilities=capabilities or [],
                model=model,
            )
        )
        self._running = False

    async def start(self) -> None:
        """Start the CLI agent and connect to Agora."""
        self._proc = await self._pty.spawn_agent("main", self._command)
        self._running = True
        logger.info("CLI Bridge started for %s", self._adapter.agent_type)

    async def run_loop(self, timeout: float = 5.0) -> None:
        """Main loop: read output, parse, route tool calls."""
        while self._running and self._proc.is_alive():
            data = await self._proc.read_output()
            if not data:
                await asyncio.sleep(0.1)
                continue
            tool_calls = self._adapter.parse_output(data.encode("utf-8"))
            for call in tool_calls:
                result = await self._handle_tool_call(call)
                response = self._adapter.format_result(result)
                await self._proc.write_input(response.decode("utf-8"))

    async def _handle_tool_call(self, call: object) -> ToolResult:
        """Handle a parsed tool call — route via Agora or execute."""
        logger.info("Tool call: %s", call)
        return ToolResult(
            call_id=getattr(call, "call_id", ""),
            name=getattr(call, "name", ""),
            output="Tool execution not yet implemented",
        )

    async def stop(self) -> None:
        """Stop the CLI agent and disconnect from Agora."""
        self._running = False
        await self._pty.terminate("main")
        logger.info("CLI Bridge stopped")


async def main(args: Optional[list[str]] = None) -> None:
    """CLI entry point for the bridge."""
    import argparse

    parser = argparse.ArgumentParser(description="Agora CLI Bridge")
    parser.add_argument("--type", required=True, help="Agent type")
    parser.add_argument("--command", nargs="+", required=True)
    parser.add_argument("--coordinator", default="http://localhost:8765")
    parser.add_argument("--agent-id", default="")
    parser.add_argument("--agent-name", default="")
    parsed = parser.parse_args(args)

    bridge = CLIBridge(
        agent_type=parsed.type,
        command=parsed.command,
        coordinator_url=parsed.coordinator,
        agent_id=parsed.agent_id,
        agent_name=parsed.agent_name,
    )
    await bridge.start()
    try:
        await bridge.run_loop()
    except KeyboardInterrupt:
        pass
    finally:
        await bridge.stop()
