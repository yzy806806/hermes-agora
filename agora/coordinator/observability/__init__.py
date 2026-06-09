"""Observability foundation: metrics, events, and traces."""

from .metrics import metrics, init_metrics, collect_metrics, update_uptime
from .events import EventType, Event, EventEmitter
from .trace import Trace, get_trace_id, new_trace

__all__ = [
    "metrics", "init_metrics", "collect_metrics", "update_uptime",
    "EventType", "Event", "EventEmitter",
    "Trace", "get_trace_id", "new_trace",
]
