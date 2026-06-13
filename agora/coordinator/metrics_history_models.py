"""Models for the metrics history API endpoint (Phase 13.3a).

Provides Chart.js-compatible data structure for dashboard charts.
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class MetricType(str, Enum):
    """Supported metric types for history queries."""
    agent_activity = "agent_activity"
    task_throughput = "task_throughput"
    discussion_outcomes = "discussion_outcomes"
    pipeline_success_rate = "pipeline_success_rate"
    rate_limit_usage = "rate_limit_usage"


class RangePeriod(str, Enum):
    """Supported time range periods."""
    one_hour = "1h"
    six_hours = "6h"
    one_day = "1d"
    seven_days = "7d"
    thirty_days = "30d"


class DatasetEntry(BaseModel):
    """A single dataset within a chart response."""
    label: str = ""
    data: list[int | float] = []


class MetricsHistoryResponse(BaseModel):
    """Chart.js-compatible response for metrics history.

    Format: {metric, range, labels, datasets}
    Labels are time bucket identifiers; datasets hold values.
    """
    metric: str = ""
    range: str = ""
    labels: list[str] = []
    datasets: list[DatasetEntry] = []
