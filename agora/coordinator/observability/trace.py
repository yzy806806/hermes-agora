"""Trace context propagation for Agora Coordinator.

Provides Trace dataclass and context-variable based trace_id
propagation across REST API (X-Trace-Id header) and
WebSocket messages (trace_id field).
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

# Context variable for the current trace_id
_trace_var: ContextVar[str] = ContextVar("trace_id", default="")


@dataclass
class Trace:
    """Trace context carried across request boundaries."""
    trace_id: str
    motion_id: Optional[str]
    agent_id: Optional[str]
    span_id: str
    parent_span_id: Optional[str]
    start_time: float

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "motion_id": self.motion_id,
            "agent_id": self.agent_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
        }


def new_trace(
    motion_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
) -> Trace:
    """Create a new Trace with fresh trace_id and span_id."""
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())[:8]
    import time
    return Trace(
        trace_id=trace_id,
        motion_id=motion_id,
        agent_id=agent_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        start_time=time.time(),
    )


def get_trace_id() -> str:
    """Get the current trace_id from context, or empty string."""
    return _trace_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set the current trace_id in context."""
    _trace_var.set(trace_id)


def new_span(parent: Trace) -> Trace:
    """Create a child span under an existing trace."""
    import time
    return Trace(
        trace_id=parent.trace_id,
        motion_id=parent.motion_id,
        agent_id=parent.agent_id,
        span_id=str(uuid.uuid4())[:8],
        parent_span_id=parent.span_id,
        start_time=time.time(),
    )
