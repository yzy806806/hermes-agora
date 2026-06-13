"""Pipeline and rate-limit metrics queries (Phase 13.3a).

Split from metrics_history_extra.py to stay under 80-line constraint.
Contains: pipeline_success_rate, rate_limit_usage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import aiosqlite

logger = logging.getLogger(__name__)

RANGE_DAYS = {"1h": 1 / 24, "6h": 6 / 24, "1d": 1, "7d": 7, "30d": 30}


async def query_pipeline_success_rate(
    db: aiosqlite.Connection, range_key: str,
    project_id: str | None = None,
) -> dict:
    """Pipeline success vs failure counts from pipeline_runs."""
    days = RANGE_DAYS[range_key]
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    rows = await db.execute_fetchall(
        """SELECT
           CASE WHEN phase = 'completed' THEN 'success' ELSE 'failed' END AS outcome,
           COUNT(*) AS cnt
           FROM pipeline_runs WHERE started_at >= ?
           GROUP BY outcome ORDER BY outcome""",
        [cutoff],
    )
    labels = [r[0] for r in rows]
    data = [r[1] for r in rows]
    return {"labels": labels, "datasets": [{"label": "Count", "data": data}]}


async def query_rate_limit_usage(
    db: aiosqlite.Connection, range_key: str,
    project_id: str | None = None,
) -> dict:
    """TPM usage per agent from rate_limit_usage table."""
    days = RANGE_DAYS[range_key]
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).strftime("%Y-%m-%dT%H:%M:%S")
    rows = await db.execute_fetchall(
        """SELECT agent_id,
           SUM(tokens_consumed) AS total_tokens,
           MAX(tpm_limit) AS tpm_limit
           FROM rate_limit_usage WHERE last_updated >= ?
           GROUP BY agent_id ORDER BY total_tokens DESC""",
        [cutoff],
    )
    labels = [r[0] for r in rows]
    used = [r[1] for r in rows]
    limits = [r[2] for r in rows]
    return {
        "labels": labels,
        "datasets": [
            {"label": "Tokens Used", "data": used},
            {"label": "TPM Limit", "data": limits},
        ],
    }
