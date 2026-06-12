"""Agora Hermes Bridge — connects Hermes profiles to Agora Coordinator.

Translates between Hermes internal mechanisms (kanban, cron, tools)
and Agora WebSocket messages via the Agent SDK.

Public API:
    HermesAdapter — bridge implementation for Hermes profiles
"""

from agora_hermes_bridge.adapter import HermesAdapter

__version__ = "0.1.0"

__all__ = ["HermesAdapter", "__version__"]
