"""HermesAdapter — maps Hermes kanban tasks to Agora WS messages."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from agora_agent_sdk import AbstractBridge, AgoraAgentClient
from agora_agent_sdk.protocol import TaskNode

from agora_hermes_bridge.cli import hermes_available, run_hermes
from agora_hermes_bridge.polling import poll_kanban_task

logger = logging.getLogger(__name__)


class HermesAdapter(AbstractBridge):
    """Bridge for Hermes profiles. Translates kanban/cron ↔ Agora WS."""

    def __init__(
        self, client: AgoraAgentClient, profile_name: str,
        poll_interval: int = 30, poll_max: int = 120,
    ) -> None:
        super().__init__(client)
        self.profile = profile_name
        self._poll_interval = poll_interval
        self._poll_max = poll_max
        self._kanban_map: dict[str, str] = {}
        if not hermes_available():
            raise RuntimeError("'hermes' CLI not found — bridge requires it")

    async def on_task_assigned(self, task: TaskNode) -> None:
        """TASK_ASSIGNED → hermes kanban create."""
        assignee = self.profile
        result = await run_hermes([
            "kanban", "create", task.title,
            "--assignee", assignee, "--json",
        ])
        kb_id = result.get("task_id", "")
        if not kb_id:
            logger.error("kanban create returned no id for %s", task.task_id)
            return
        self._kanban_map[task.task_id] = kb_id
        logger.info("Mapped Agora task %s → kanban %s", task.task_id, kb_id)
        await self.client.report_task_start(task.task_id)
        asyncio.create_task(poll_kanban_task(
            self.client, task.task_id, kb_id,
            self._kanban_map, self._poll_interval, self._poll_max,
        ))

    async def on_discussion_message(self, motion_id: str, content: str) -> None:
        """SPEECH_ADDED → write to Hermes prompt channel."""
        state = {
            "motion_id": motion_id, "content": content,
            "prompt_id": str(uuid.uuid4())[:8], "profile": self.profile,
        }
        await run_hermes([
            "kanban", "comment",
            self._kanban_map.get(motion_id, motion_id),
            json.dumps(state),
        ])
        logger.info("Forwarded discussion %s to Hermes", motion_id[:8])

    async def on_devils_advocate(self, motion_id: str, topic: str) -> str:
        """Return a devil's advocate response from Hermes profile."""
        result = await run_hermes([
            "chat", "prompt",
            f"[Devil's Advocate] Motion {motion_id}: {topic}",
            "--profile", self.profile, "--json",
        ])
        return result.get("response", "")
