"""Base adapter ABC for CLI Bridge.

Each CLI agent (Codex, Claude Code, OpenClaw, etc.) implements
this interface to translate its tool calls into Agora format.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Normalized tool call from any CLI agent."""

    call_id: str = ""
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class ToolResult:
    """Result of executing a tool call, ready to send back."""

    call_id: str = ""
    name: str = ""
    output: str = ""
    error: str | None = None
    success: bool = True


class BaseCLIAdapter(ABC):
    """Abstract base class for CLI agent adapters.

    Subclasses must implement:
    - parse_output: turn raw stdout bytes into ToolCall list
    - format_result: turn ToolResult into bytes the agent expects
    """

    agent_type: str = "unknown"

    @abstractmethod
    def parse_output(self, raw: bytes) -> list[ToolCall]:
        """Parse raw stdout from the CLI agent into ToolCall list."""

    @abstractmethod
    def format_result(self, result: ToolResult) -> bytes:
        """Format a ToolResult into bytes the CLI agent can consume."""

    def build_prompt(self, task_description: str) -> bytes:
        """Build the initial prompt to send to the agent's stdin.

        Default: just the task description as UTF-8 text.
        """
        return task_description.encode("utf-8")

    def is_tool_call(self, line: bytes) -> bool:
        """Quick check if a stdout line contains a tool call."""
        return False
