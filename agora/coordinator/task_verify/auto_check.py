"""Auto-verify logic — file existence checks (Phase 9 scope)."""

from __future__ import annotations

import os


async def auto_verify(task: dict) -> tuple[bool, str]:
    """Run automated verification checks.

    Phase 9 scope: only file existence check.
    Returns (passed, reason).
    """
    artifact_paths = task.get("artifact_paths") or []

    missing = [p for p in artifact_paths if not os.path.exists(p)]
    if missing:
        return False, f"Missing artifacts: {', '.join(missing)}"

    if not artifact_paths:
        return True, "No artifacts declared; auto-accepting"

    return True, "All artifacts present"
