"""CLI Bridge adapters — tool call format translators.

Each adapter converts between a specific CLI agent's tool call
format and Agora's normalized ToolCall/ToolResult format.
"""
from .base import BaseCLIAdapter, ToolCall, ToolResult
from .codex_adapter import CodexAdapter
from .claude_adapter import ClaudeAdapter
from .openclaw_adapter import OpenClawAdapter, PicoClawAdapter

ADAPTER_MAP: dict[str, type[BaseCLIAdapter]] = {
    "codex": CodexAdapter,
    "claude": ClaudeAdapter,
    "openclaw": OpenClawAdapter,
    "picoclaw": PicoClawAdapter,
}


def get_adapter(agent_type: str) -> BaseCLIAdapter:
    """Get an adapter instance by agent type name."""
    cls = ADAPTER_MAP.get(agent_type)
    if cls is None:
        raise ValueError(
            f"Unknown agent type: {agent_type!r}. "
            f"Available: {list(ADAPTER_MAP)}"
        )
    return cls()


__all__ = [
    "BaseCLIAdapter",
    "ToolCall",
    "ToolResult",
    "CodexAdapter",
    "ClaudeAdapter",
    "OpenClawAdapter",
    "PicoClawAdapter",
    "ADAPTER_MAP",
    "get_adapter",
]
