"""Task Generator — convert discussion results into Kanban tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import aiohttp

from .discussion_driver import DiscussionResult

logger = logging.getLogger(__name__)

# Category → default assignee mapping
ASSIGNEE_MAP: dict[str, str] = {
    "development": "dev-merger",
    "review": "reviewer",
    "research": "planner",
    "release": "releaser",
    "documentation": "dev-merger",
}


@dataclass
class TaskSpec:
    """Specification for a Kanban task to be created."""
    title: str
    description: str
    assignee: str
    priority: int = 0
    parent_task_id: Optional[str] = None
    skills: list[str] = field(default_factory=list)
    workspace_kind: str = "scratch"


class TaskGenerator:
    """Generate Kanban tasks from discussion results."""

    def __init__(
        self, kanban_url: str = "http://localhost:8000",
        board: str = "default",
    ) -> None:
        self.kanban_url = kanban_url.rstrip("/")
        self.board = board

    async def generate_tasks(
        self, discussion_result: dict,
        parent_task_id: Optional[str] = None,
    ) -> list[str]:
        """Create Kanban tasks from a discussion result's action_items."""
        task_ids: list[str] = []
        action_items = discussion_result.get("action_items", [])
        for idx, item in enumerate(action_items):
            category = item.get("category", "development")
            spec = TaskSpec(
                title=item.get("title", f"Task {idx + 1}"),
                description=item.get("description", ""),
                assignee=self._infer_assignee(category),
                priority=item.get("priority", idx),
                parent_task_id=parent_task_id,
                skills=item.get("skills", []),
            )
            task_id = await self._create_task(spec)
            task_ids.append(task_id)
        logger.info("Generated %d tasks from discussion", len(task_ids))
        return task_ids

    async def from_discussion_result(
        self, result: DiscussionResult,
        parent_task_id: Optional[str] = None,
    ) -> list[str]:
        """Generate tasks from a DiscussionResult object."""
        payload = {
            "action_items": result.recommended_actions,
        }
        return await self.generate_tasks(payload, parent_task_id)

    async def _create_task(self, spec: TaskSpec) -> str:
        """Create a single Kanban task via the API."""
        payload = {
            "title": spec.title,
            "body": spec.description,
            "assignee": spec.assignee,
            "priority": spec.priority,
            "board": self.board,
        }
        if spec.skills:
            payload["skills"] = spec.skills
        if spec.parent_task_id:
            payload["parents"] = [spec.parent_task_id]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.kanban_url}/api/kanban/tasks",
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data["task_id"]
        except aiohttp.ClientError as exc:
            logger.error("Task creation failed: %s", exc)
            raise RuntimeError(f"Kanban task creation failed: {exc}") from exc

    def _infer_assignee(self, category: str) -> str:
        """Map a category to a default assignee profile."""
        return ASSIGNEE_MAP.get(category, "dev-merger")

    async def create_approval_task(
        self, motion_id: str, decision: str,
    ) -> str:
        """Create a user-approval Kanban task."""
        spec = TaskSpec(
            title=f"[审批] 讨论结果 {motion_id}",
            description=f"请审批开发方向讨论结果：{decision}",
            assignee="user",
            priority=100,
            skills=["approval"],
        )
        return await self._create_task(spec)
