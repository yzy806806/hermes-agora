"""NotificationManager — creates and pushes notifications (Phase 13.4b).

Responsibilities:
- async create(type, title, body, project_id, priority) -> Notification
- _push_to_dashboards(notif) — broadcast NOTIFICATION to subscribed WS clients
- Integration helpers for pipeline events (completed, failed, etc.)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .notification_models import Notification, NotificationPriority, NotificationType

logger = logging.getLogger(__name__)


class NotificationManager:
    """Stores and delivers notifications to dashboard clients."""

    def __init__(self, storage: Any, dashboard_hub: Any = None) -> None:
        self._storage = storage
        self._hub = dashboard_hub

    def set_dashboard_hub(self, hub: Any) -> None:
        """Inject the dashboard hub (called after app init)."""
        self._hub = hub

    async def create(
        self,
        type: str,
        title: str,
        body: str,
        project_id: str,
        priority: str = "medium",
    ) -> Notification:
        """Create a notification and push to connected dashboards."""
        notif = Notification(
            id=uuid.uuid4().hex[:16],
            type=NotificationType(type),
            title=title,
            body=body,
            project_id=project_id,
            priority=NotificationPriority(priority),
            created_at=datetime.now(timezone.utc),
            read=False,
        )
        await self._storage.create_notification(
            type=notif.type.value,
            title=notif.title,
            body=notif.body,
            project_id=notif.project_id,
            priority=notif.priority.value,
        )
        await self._push_to_dashboards(notif)
        return notif

    async def _push_to_dashboards(self, notif: Notification) -> int:
        """Send NOTIFICATION message to all subscribed dashboard WS clients."""
        if self._hub is None:
            return 0
        payload = notif.model_dump(mode="json")
        count = await self._hub.broadcast_event(
            "NOTIFICATION", payload, channel="notifications",
        )
        logger.info("Pushed %s notification to %d clients", notif.type.value, count)
        return count

    # -- Pipeline event helpers --

    async def notify_pipeline_completed(
        self, pipeline_id: str, project_id: str, summary: str,
    ) -> Notification:
        return await self.create(
            type=NotificationType.PIPELINE_COMPLETED.value,
            title=f"Pipeline {pipeline_id} completed",
            body=summary,
            project_id=project_id,
            priority=NotificationPriority.HIGH.value,
        )

    async def notify_pipeline_failed(
        self, pipeline_id: str, project_id: str, error: str,
    ) -> Notification:
        return await self.create(
            type=NotificationType.PIPELINE_FAILED.value,
            title=f"Pipeline {pipeline_id} failed",
            body=error,
            project_id=project_id,
            priority=NotificationPriority.CRITICAL.value,
        )

    async def notify_review_requested(
        self, pipeline_id: str, project_id: str, files: list[str],
    ) -> Notification:
        return await self.create(
            type=NotificationType.REVIEW_REQUESTED.value,
            title=f"Review requested for pipeline {pipeline_id}",
            body=f"Files to review: {', '.join(files[:5])}",
            project_id=project_id,
            priority=NotificationPriority.MEDIUM.value,
        )

    async def notify_agent_offline(
        self, agent_id: str, project_id: str,
    ) -> Notification:
        return await self.create(
            type=NotificationType.AGENT_OFFLINE.value,
            title=f"Agent {agent_id} went offline",
            body=f"Agent {agent_id} heartbeat lost",
            project_id=project_id,
            priority=NotificationPriority.HIGH.value,
        )
