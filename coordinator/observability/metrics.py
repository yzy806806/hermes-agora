"""Prometheus metrics for Agora Coordinator.

Exposes 20+ indicators covering discussions, agents,
votes, tools, and coordinator internals.
"""

from __future__ import annotations

import time

from prometheus_client import (
    Counter, Gauge, Histogram, REGISTRY,
    generate_latest, CONTENT_TYPE_LATEST,
)

_START_TIME = time.time()


class _Metrics:
    """Container for all Prometheus instruments."""

    # -- Discussion metrics --
    discussions_total = Counter(
        "agora_discussions_total",
        "Total discussions by status", ["status"],
    )
    discussion_duration = Histogram(
        "agora_discussion_duration_seconds",
        "Discussion duration", ["method", "outcome"],
    )
    discussion_rounds = Counter(
        "agora_discussion_rounds_total",
        "Discussion rounds", ["method"],
    )
    discussion_quality = Gauge(
        "agora_discussion_quality_score",
        "Quality score per motion", ["motion_id"],
    )

    # -- Agent metrics --
    agents_connected = Gauge(
        "agora_agents_connected", "Currently connected agents",
    )
    agents_registered = Counter(
        "agora_agents_registered_total",
        "Cumulative agent registrations",
    )
    agent_disconnections = Counter(
        "agora_agent_disconnections_total",
        "Agent disconnections", ["reason"],
    )

    # -- Vote metrics --
    votes_total = Counter(
        "agora_votes_total", "Vote results", ["method", "result"],
    )
    vote_participation = Gauge(
        "agora_vote_participation_ratio",
        "Vote participation ratio",
    )

    # -- Tool metrics --
    tools_calls = Counter(
        "agora_tools_calls_total", "Tool calls", ["tool", "status"],
    )
    tools_duration = Histogram(
        "agora_tools_call_duration_seconds",
        "Tool call duration", ["tool"],
    )

    # -- Coordinator metrics --
    coordinator_uptime = Gauge(
        "agora_coordinator_uptime_seconds", "Uptime in seconds",
    )
    ws_messages = Counter(
        "agora_ws_messages_total", "WS messages", ["direction", "type"],
    )
    db_size = Gauge(
        "agora_db_size_bytes", "Database size in bytes",
    )
    memory_sync_ops = Counter(
        "agora_memory_sync_ops_total", "Memory sync ops", ["status"],
    )


metrics = _Metrics()


def init_metrics() -> None:
    """Set initial gauge values on startup."""
    metrics.agents_connected.set(0)
    metrics.vote_participation.set(0)
    metrics.coordinator_uptime.set(0)
    metrics.db_size.set(0)


def update_uptime() -> None:
    """Refresh the uptime gauge."""
    metrics.coordinator_uptime.set(time.time() - _START_TIME)


def collect_metrics() -> tuple[str, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    update_uptime()
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
