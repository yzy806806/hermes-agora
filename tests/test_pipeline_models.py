"""Tests for pipeline_models: PipelinePhase enum + PipelineRun model."""

import pytest
from datetime import datetime, timezone

from agora.coordinator.pipeline_models import PipelinePhase, PipelineRun


# --- PipelinePhase tests ---

def test_phase_values():
    """All phases have correct string values."""
    assert PipelinePhase.DISCUSSING == "discussing"
    assert PipelinePhase.DECOMPOSING == "decomposing"
    assert PipelinePhase.EXECUTING == "executing"
    assert PipelinePhase.REVIEWING == "reviewing"
    assert PipelinePhase.RELEASING == "releasing"
    assert PipelinePhase.COMPLETED == "completed"
    assert PipelinePhase.FAILED == "failed"


def test_phase_from_value():
    """PipelinePhase can be constructed from string value."""
    assert PipelinePhase("executing") is PipelinePhase.EXECUTING


def test_phase_invalid_value():
    """Invalid phase value raises ValueError."""
    with pytest.raises(ValueError):
        PipelinePhase("nonexistent")


# --- PipelineRun tests ---

def test_run_defaults():
    """PipelineRun has sensible defaults."""
    run = PipelineRun(id="r1", project_id="p1", idea="test idea")
    assert run.phase is PipelinePhase.DISCUSSING
    assert run.motion_id is None
    assert run.graph_id is None
    assert run.tasks_total == 0
    assert run.tasks_completed == 0
    assert run.tasks_failed == 0
    assert run.review_outcome is None
    assert run.release_version is None
    assert run.error is None
    assert run.completed_at is None


def test_run_started_at_auto_set():
    """started_at is auto-populated with UTC now."""
    run = PipelineRun(id="r2", project_id="p1", idea="x")
    assert run.started_at is not None
    assert run.started_at.tzinfo is not None


def test_run_full_construction():
    """PipelineRun can be fully constructed with all fields."""
    now = datetime.now(timezone.utc)
    run = PipelineRun(
        id="r3", project_id="p1", idea="build feature",
        motion_id="m1", graph_id="g1",
        phase=PipelinePhase.RELEASING,
        started_at=now, completed_at=now,
        tasks_total=5, tasks_completed=4, tasks_failed=1,
        review_outcome="approved", release_version="1.0.0",
        error=None,
    )
    assert run.phase is PipelinePhase.RELEASING
    assert run.tasks_total == 5
    assert run.review_outcome == "approved"


def test_run_serialization_roundtrip():
    """PipelineRun serializes to dict and back without data loss."""
    run = PipelineRun(id="r4", project_id="p1", idea="roundtrip")
    data = run.model_dump()
    restored = PipelineRun(**data)
    assert restored.id == run.id
    assert restored.phase == run.phase
    assert restored.idea == run.idea
