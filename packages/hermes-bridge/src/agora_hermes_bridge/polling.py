"""Task completion polling for HermesAdapter.

Polls hermes kanban show until task reaches terminal state,
then reports result back to Agora via AgoraAgentClient.
"""

from __future__ import annotations

import asyncio
import logging

from agora_agent_sdk import AgoraAgentClient
from agora_hermes_bridge.cli import run_hermes

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
POLL_MAX_ATTEMPTS = 120  # 1 hour at 30s intervals


async def poll_kanban_task(
    client: AgoraAgentClient,
    agora_task_id: str,
    kanban_task_id: str,
    kanban_map: dict[str, str],
    poll_interval: int = POLL_INTERVAL_SECONDS,
    poll_max: int = POLL_MAX_ATTEMPTS,
) -> None:
    """Poll kanban task until done/failed/blocked, report to Agora."""
    for _ in range(poll_max):
        await asyncio.sleep(poll_interval)
        try:
            result = await run_hermes([
                "kanban", "show", kanban_task_id, "--json",
            ])
        except RuntimeError:
            logger.warning("Poll failed for kanban %s", kanban_task_id)
            continue
        status = result.get("status", "")
        if status == "done":
            await client.report_task_complete(agora_task_id, artifacts=[])
            kanban_map.pop(agora_task_id, None)
            logger.info("Agora task %s complete (kanban %s)", agora_task_id, kanban_task_id)
            return
        if status in ("failed", "blocked"):
            await client.report_task_failed(
                agora_task_id, error=result.get("error", "unknown"),
            )
            kanban_map.pop(agora_task_id, None)
            return
    await client.report_task_failed(
        agora_task_id, error="kanban polling timed out",
    )
    kanban_map.pop(agora_task_id, None)
