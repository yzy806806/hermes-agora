"""Tests for pipeline_errors: error hierarchy and retryable flags."""

import pytest

from agora.coordinator.pipeline_errors import (
    DecompositionFailedError,
    DiscussionFailedError,
    ExecutionFailedError,
    PipelineError,
    ReleaseFailedError,
    ReviewFailedError,
)
from agora.coordinator.pipeline_models import PipelinePhase


# --- PipelineError base ---

def test_pipeline_error_base():
    """PipelineError stores phase and retryable flag."""
    err = PipelineError(PipelinePhase.EXECUTING, "boom", retryable=True)
    assert err.phase is PipelinePhase.EXECUTING
    assert err.retryable is True
    assert "[executing] boom" in str(err)


def test_pipeline_error_not_retryable():
    """PipelineError with retryable=False."""
    err = PipelineError(PipelinePhase.DISCUSSING, "oops", retryable=False)
    assert err.retryable is False


# --- Specific error types ---

def test_discussion_failed_not_retryable():
    err = DiscussionFailedError("no consensus")
    assert err.phase is PipelinePhase.DISCUSSING
    assert err.retryable is False


def test_decomposition_failed_not_retryable():
    err = DecompositionFailedError("LLM failed")
    assert err.phase is PipelinePhase.DECOMPOSING
    assert err.retryable is False


def test_execution_failed_retryable():
    err = ExecutionFailedError("task crashed")
    assert err.phase is PipelinePhase.EXECUTING
    assert err.retryable is True


def test_review_failed_retryable():
    err = ReviewFailedError("reviewer timeout")
    assert err.retryable is True


def test_release_failed_retryable():
    err = ReleaseFailedError("push failed")
    assert err.retryable is True


# --- Inheritance ---

def test_all_errors_are_pipeline_error():
    """All specific errors inherit from PipelineError."""
    for cls in (DiscussionFailedError, DecompositionFailedError,
                ExecutionFailedError, ReviewFailedError, ReleaseFailedError):
        err = cls("test")
        assert isinstance(err, PipelineError)
        assert isinstance(err, Exception)
