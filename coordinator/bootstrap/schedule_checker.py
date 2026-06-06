"""Schedule checker — evaluate cron-based and event-based triggers."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


async def check_scheduled_triggers(db_path: str) -> list[dict]:
    """Return due scheduled triggers (next_run <= now or NULL)."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM bootstrap_schedules
               WHERE enabled = 1
               AND (next_run IS NULL OR next_run <= ?)
               ORDER BY next_run ASC""",
            [now],
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def update_schedule_run(
    db_path: str, schedule_id: int,
    last_run: str, next_run: Optional[str],
) -> None:
    """Update a schedule's last_run and next_run timestamps."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """UPDATE bootstrap_schedules
               SET last_run = ?, next_run = ?
               WHERE id = ?""",
            [last_run, next_run, schedule_id],
        )
        await db.commit()


async def check_github_issues(
    repo: str, label: str = "needs-discussion",
) -> list[dict]:
    """Check GitHub issues for new discussion needs.

    Uses gh CLI to find issues with the given label.
    Returns a list of dicts with title, number, and url.
    """
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "-R", repo,
             "--label", label, "--state", "open",
             "--json", "number,title,url"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning("gh issue list failed: %s", result.stderr)
            return []
        import json
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("check_github_issues error: %s", exc)
        return []
