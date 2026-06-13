"""Pipeline error types (Phase 13)."""

from __future__ import annotations

from agora.coordinator.pipeline_models import PipelinePhase


class PipelineError(Exception):
    """Base error for pipeline failures."""

    def __init__(self, phase: PipelinePhase, message: str,
                 retryable: bool = False) -> None:
        self.phase = phase
        self.retryable = retryable
        super().__init__(f"[{phase.value}] {message}")


class DiscussionFailedError(PipelineError):
    """Discussion phase failed (non-retryable)."""

    def __init__(self, message: str) -> None:
        super().__init__(PipelinePhase.DISCUSSING, message, retryable=False)


class DecompositionFailedError(PipelineError):
    """Task decomposition failed (non-retryable)."""

    def __init__(self, message: str) -> None:
        super().__init__(PipelinePhase.DECOMPOSING, message, retryable=False)


class ExecutionFailedError(PipelineError):
    """Execution phase failed (retryable)."""

    def __init__(self, message: str) -> None:
        super().__init__(PipelinePhase.EXECUTING, message, retryable=True)


class ReviewFailedError(PipelineError):
    """Review phase failed (retryable)."""

    def __init__(self, message: str) -> None:
        super().__init__(PipelinePhase.REVIEWING, message, retryable=True)


class ReleaseFailedError(PipelineError):
    """Release phase failed (retryable)."""

    def __init__(self, message: str) -> None:
        super().__init__(PipelinePhase.RELEASING, message, retryable=True)
