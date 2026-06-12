"""ToolAdapter — translates tool calls between agent formats.

Each CLI agent has its own tool call format. ToolAdapter
normalizes them into Agora's standard tool call format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """Normalized representation of a tool call."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    raw: str = ""  # Original raw text for debugging


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    output: str
    success: bool = True
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolAdapter:
    """Translates between different agent tool call formats.

    Subclasses override parse_tool_call() and format_tool_result()
    for specific agent types (codex, claude-code, openclaw, etc.).
    """

    def parse_tool_call(
        self, agent_type: str, raw: str
    ) -> ToolCall:
        """Parse a tool call from the agent's raw output.

        Args:
            agent_type: The agent type (e.g. "codex", "claude-code").
            raw: Raw text output from the agent.

        Returns:
            Normalized ToolCall object.
        """
        # Default: treat entire raw text as a single tool call
        return ToolCall(name="unknown", raw=raw)

    def format_tool_result(
        self, agent_type: str, result: ToolResult
    ) -> str:
        """Format a tool result for the agent to consume.

        Args:
            agent_type: The agent type (e.g. "codex", "claude-code").
            result: ToolResult from executing the tool.

        Returns:
            Formatted string the agent can process.
        """
        if result.success:
            return result.output
        return f"ERROR: {result.error}\n{result.output}"
