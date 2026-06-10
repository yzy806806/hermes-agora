"""Review delegation — find reviewer agents and send TASK_VERIFY."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Round-robin index for reviewer selection
_rr_index = [0]


async def delegate_review(
    task: dict, storage: Any, hub: Any,
) -> None:
    """Send TASK_VERIFY to a reviewer agent.

    Find online agents with 'review' capability, pick one round-robin.
    If no reviewer available, leave task DONE and log warning.
    """
    online_ids = set(hub.get_online_agents())
    all_agents = await storage.list_agents(online_only=False)

    reviewers: list[dict] = []
    for agent in all_agents:
        aid = agent["agent_id"]
        if aid not in online_ids:
            continue
        caps = agent.get("capabilities") or []
        if isinstance(caps, str):
            caps = json.loads(caps)
        if "review" in caps:
            reviewers.append(agent)

    if not reviewers:
        logger.warning(
            "No reviewer available for task %s; leaving DONE",
            task["id"],
        )
        return

    n = len(reviewers)
    idx = _rr_index[0] % n
    _rr_index[0] += 1
    reviewer_id = reviewers[idx]["agent_id"]

    msg = {
        "type": "TASK_VERIFY",
        "motion_id": task.get("motion_id"),
        "payload": {
            "task_id": task["id"],
            "title": task.get("title", ""),
            "assigned_to": task.get("assigned_to"),
            "artifact_paths": task.get("artifact_paths", []),
            "description": task.get("description", ""),
        },
    }
    sent = await hub.send(reviewer_id, msg)
    if sent:
        logger.info("Delegated review of task %s to %s",
                     task["id"], reviewer_id)
    else:
        logger.warning("Failed to send TASK_VERIFY to %s", reviewer_id)
