"""Default hook method implementations for AgoraPlugin (Phase 10.3).

Extracted from plugin.py to keep file sizes under 80 lines.
Plugins override only the hooks they need; the rest are no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agora.coordinator.plugin import HookContext


class PluginHooks:
    """Mixin providing default no-op hook handlers.

    AgoraPlugin inherits this so every hook method is available
    without requiring plugins to implement them all.
    """

    async def on_discussion_created(self, ctx: HookContext) -> None:
        pass

    async def on_discussion_ended(self, ctx: HookContext) -> None:
        pass

    async def on_task_created(self, ctx: HookContext) -> None:
        pass

    async def on_task_completed(self, ctx: HookContext) -> None:
        pass

    async def on_task_failed(self, ctx: HookContext) -> None:
        pass

    async def on_agent_registered(self, ctx: HookContext) -> None:
        pass

    async def on_agent_disconnected(self, ctx: HookContext) -> None:
        pass

    async def on_motion_passed(self, ctx: HookContext) -> None:
        pass

    async def on_motion_rejected(self, ctx: HookContext) -> None:
        pass
