"""Discussion outcomes metrics query (Phase 13.3a).

Split from metrics_history.py to stay under 80-line constraint.
Contains: discussion_outcomes only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import aiosqlite

logger = logging.getLogger(__name__)

RANGE_DAYS = {"1h": 1 / 24, "6h": 6 / 24, "1d": 1, "7d": 7, "30d": 30}


async def query_discussion_outcomes(
    db: aiosqlite.Connection, range_key: str,
    project_id: str | None = None,
) -> dict:
    """Motion outcomes (consensus/deadlock/timeout) from motions."""
    days = RANGE_DAYS[range_key]
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    rows = await db.execute_fetchall(
        """SELECT COALESCE(decision, 'no_consensus') AS outcome,
           COUNT(*) AS cnt
           FROM motions WHERE closed_at >= ?
           GROUP BY outcome ORDER BY outcome""",
        [cutoff],
    )
    labels = [r[0] for r in rows]
    data = [r[1] for r in rows]
    return {"labels": labels, "datasets": [{"label": "Count", "data": data}]}
