"""Plugin base classes and models for the Agora Plugin Ecosystem (Phase 10.3).

Provides HookPoint enum, HookContext model, PluginManifest model,
and the AgoraPlugin ABC that all plugins must subclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from agora.coordinator.plugin_hooks import PluginHooks

if TYPE_CHECKING:
    from agora.coordinator.plugin_manager import PluginCoordinator


class HookPoint(str, Enum):
    """Lifecycle events that plugins can hook into."""

    DISCUSSION_CREATED = "discussion.created"
    DISCUSSION_ENDED = "discussion.ended"
    TASK_CREATED = "task.created"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    AGENT_REGISTERED = "agent.registered"
    AGENT_DISCONNECTED = "agent.disconnected"
    MOTION_PASSED = "motion.passed"
    MOTION_REJECTED = "motion.rejected"
    CUSTOM = "custom"


class HookContext(BaseModel):
    """Context passed to hook handlers."""

    hook_point: HookPoint
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: Optional[str] = None
    tenant_id: Optional[str] = None


class PluginManifest(BaseModel):
    """Metadata about a plugin."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    hook_points: list[HookPoint] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    min_agora_version: str = "0.10.0"


class AgoraPlugin(PluginHooks, ABC):
    """Abstract base class for all Agora plugins.

    Inherit from this and implement on_load() / on_unload().
    Hook methods (on_task_created, etc.) are no-ops by default.
    """

    manifest: PluginManifest

    @abstractmethod
    async def on_load(self, coordinator: PluginCoordinator) -> None:
        """Called when plugin is loaded. Register hooks, endpoints, etc."""
        ...

    @abstractmethod
    async def on_unload(self) -> None:
        """Called when plugin is unloaded. Clean up resources."""
        ...

    async def health_check(self) -> bool:
        """Periodic health check. Return False to trigger reload."""
        return True
