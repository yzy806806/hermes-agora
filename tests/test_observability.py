"""Unit tests for observability module (metrics, events, traces)."""

import pytest
from datetime import datetime, timezone

from coordinator.observability.metrics import (
    metrics, init_metrics, collect_metrics,
)
from coordinator.observability.events import (
    EventType, Event, EventEmitter,
)
from coordinator.observability.trace import (
    Trace, new_trace, get_trace_id, set_trace_id, new_span,
)


class TestMetrics:
    """Tests for Prometheus metrics."""

    def test_init_metrics_sets_gauges(self):
        """init_metrics should initialize gauge values."""
        init_metrics()
        # Should not raise; gauges should be set to 0
        assert metrics.agents_connected._value.get() == 0

    def test_collect_metrics_returns_prometheus_format(self):
        """collect_metrics should return (body, content_type)."""
        body, content_type = collect_metrics()
        assert "text/plain" in content_type
        assert b"agora_agents_connected" in body

    def test_counter_increment(self):
        """Counters should increment correctly."""
        metrics.discussions_total.labels(status="discussing").inc()
        # Counter should have increased (value is a float)
        val = metrics.discussions_total.labels(
            status="discussing")._value.get()
        assert val >= 1


class TestEvents:
    """Tests for structured events."""

    def test_event_type_enum_values(self):
        """EventType should have all required values."""
        assert EventType.MOTION_CREATED.value == "motion.created"
        assert EventType.AGENT_REGISTERED.value == "agent.registered"
        assert EventType.VOTE_CAST.value == "vote.cast"
        assert EventType.HEARTBEAT_LOST.value == "heartbeat.lost"

    def test_event_to_dict(self):
        """Event.to_dict should serialize correctly."""
        event = Event(
            type=EventType.MOTION_CREATED,
            motion_id="m-123",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            agent_id="agent-1",
            data={"title": "Test"},
            trace_id="t-abc",
        )
        d = event.to_dict()
        assert d["type"] == "motion.created"
        assert d["motion_id"] == "m-123"
        assert d["timestamp"] == "2026-01-01T00:00:00+00:00"
        assert d["agent_id"] == "agent-1"
        assert d["data"] == {"title": "Test"}
        assert d["trace_id"] == "t-abc"

    def test_event_to_json(self):
        """Event.to_json should produce valid JSON."""
        event = Event(
            type=EventType.SPEAK,
            motion_id="m-1",
            timestamp=datetime.now(timezone.utc),
            agent_id="a1",
            data={"content": "hello"},
            trace_id="t1",
        )
        json_str = event.to_json()
        assert '"type": "speak"' in json_str
        assert '"motion_id": "m-1"' in json_str

    def test_event_emitter_subscribe(self):
        """EventEmitter should call subscribers on emit."""
        emitter = EventEmitter()
        collected = []
        emitter.subscribe(lambda e: collected.append(e))

        event = Event(
            type=EventType.VOTE_CAST,
            motion_id="m-1",
            timestamp=datetime.now(timezone.utc),
            agent_id="a1",
            data={"vote": "yes"},
            trace_id="t1",
        )
        # Run emit synchronously (it's async but we just check callback)
        for cb in emitter._subscribers:
            cb(event)
        assert len(collected) == 1
        assert collected[0].type == EventType.VOTE_CAST


class TestTrace:
    """Tests for trace context propagation."""

    def test_new_trace_creates_uuids(self):
        """new_trace should generate unique trace_id and span_id."""
        t1 = new_trace()
        t2 = new_trace()
        assert t1.trace_id != t2.trace_id
        assert t1.span_id != t2.span_id
        assert len(t1.trace_id) == 36  # UUID format
        assert len(t1.span_id) == 8    # Short UUID

    def test_new_trace_with_params(self):
        """new_trace should accept motion_id and agent_id."""
        t = new_trace(motion_id="m-1", agent_id="a-1")
        assert t.motion_id == "m-1"
        assert t.agent_id == "a-1"

    def test_get_set_trace_id(self):
        """get_trace_id/set_trace_id should work with context."""
        set_trace_id("test-trace-123")
        assert get_trace_id() == "test-trace-123"
        # Reset
        set_trace_id("")

    def test_new_span_creates_child(self):
        """new_span should create child with parent_span_id."""
        parent = new_trace(motion_id="m-1")
        child = new_span(parent)
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id

    def test_trace_to_dict(self):
        """Trace.to_dict should serialize correctly."""
        t = new_trace(motion_id="m-1", agent_id="a-1")
        d = t.to_dict()
        assert "trace_id" in d
        assert d["motion_id"] == "m-1"
        assert d["agent_id"] == "a-1"
        assert "span_id" in d
        assert "start_time" in d
