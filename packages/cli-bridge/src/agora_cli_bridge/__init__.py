"""Agora CLI Bridge — connect CLI-based agents to Agora Coordinator.

Supports Codex, Claude Code, OpenClaw, and PicoClaw agents
via PTY subprocess management and tool call translation.
"""
from .adapters import (
    BaseCLIAdapter,
    ToolCall,
    ToolResult,
    CodexAdapter,
    ClaudeAdapter,
    OpenClawAdapter,
    PicoClawAdapter,
    get_adapter,
)
from .pty_manager import PtyManager
from .main import CLIBridge

__version__ = "0.1.0"

__all__ = [
    "BaseCLIAdapter",
    "ToolCall",
    "ToolResult",
    "CodexAdapter",
    "ClaudeAdapter",
    "OpenClawAdapter",
    "PicoClawAdapter",
    "get_adapter",
    "PtyManager",
    "CLIBridge",
]
