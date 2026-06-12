"""Agora Agent SDK — lightweight client for connecting agents to Agora."""

from .protocol import (
    AgentConfig,
    MessageType,
    WSMessage,
    RegistrationResult,
    MotionResult,
    SpeechResult,
    VoteResult,
    TaskNode,
)
from .config import AgentConnectionConfig
from .client import AgoraAgentClient
from .bridge import AbstractBridge
from .tool_adapter import ToolAdapter, ToolCall, ToolResult
from .session import SessionStore
from .models import SessionRecord, SessionFilter, SessionNote

__version__ = "0.1.0"

__all__ = [
    "AgoraAgentClient",
    "AgentConnectionConfig",
    "AbstractBridge",
    "AgentConfig",
    "MessageType",
    "WSMessage",
    "RegistrationResult",
    "MotionResult",
    "SpeechResult",
    "VoteResult",
    "TaskNode",
    "ToolAdapter",
    "ToolCall",
    "ToolResult",
    "SessionStore",
    "SessionRecord",
    "SessionFilter",
    "SessionNote",
    "__version__",
]
