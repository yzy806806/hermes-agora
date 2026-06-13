"""Tests for release integration (Phase 13.1d)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agora.coordinator.pipeline_release_models import (
    ReleaseRequest, ReleaseResult,
)
from agora.coordinator.pipeline_release_agent import find_release_agent
from agora.coordinator.pipeline_phase_release import (
    trigger_release, process_release_result,
)
from agora.coordinator.pipeline_errors import ReleaseFailedError


class TestReleaseModels:
    def test_release_request_defaults(self):
        r = ReleaseRequest(
            pipeline_id="p1", project_id="proj",
            graph_id="g1",
        )
        assert r.changed_files == []
        assert r.review_summary == ""

    def test_release_result_success(self):
        r = ReleaseResult(
            pipeline_id="p1", outcome="success",
            version="0.13.0", tag="v0.13.0",
        )
        assert r.version == "0.13.0"
        assert r.error is None

    def test_release_result_failure(self):
        r = ReleaseResult(
            pipeline_id="p1", outcome="failed",
            error="push rejected",
        )
        assert r.outcome == "failed"
        assert r.error == "push rejected"
