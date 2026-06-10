"""Simple-task check — determine if a task is auto-acceptable."""

from __future__ import annotations

import json
from typing import Any

from ..task_models import TaskStatus

# Capabilities considered safe for auto-accept
SAFE_CAPS = {"docs", "code"}


async def is_simple_task(task: dict, storage: Any = None) -> bool:
    """Determine if a task is simple enough for auto-accept.

    Simple: single artifact, no deps or all deps accepted,
    capabilities only docs or code (not security/deploy).
    """
    artifact_paths = task.get("artifact_paths") or []
    if len(artifact_paths) > 1:
        return False

    caps = task.get("required_capabilities") or []
    if isinstance(caps, str):
        caps = json.loads(caps)
    if not caps:
        return False
    if not set(caps) <= SAFE_CAPS:
        return False

    deps = task.get("depends_on") or []
    if isinstance(deps, str):
        deps = json.loads(deps)
    if deps and storage is not None:
        for dep_id in deps:
            dep = await storage.get_task(dep_id)
            if dep and dep.get("status") != TaskStatus.ACCEPTED.value:
                return False

    return True
