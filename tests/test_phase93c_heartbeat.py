"""Tests for Phase 9.3c: Heartbeat and Capabilities."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agora.coordinator.models import MessageType
from agora.coordinator.capability import capability_match_score


# --- MessageType.HEARTBEAT ---

class TestHeartbeatMessageType:
    def test_heartbeat_enum_exists(self):
        assert MessageType.HEARTBEAT == "HEARTBEAT"

    def test_heartbeat_is_string(self):
        assert isinstance(MessageType.HEARTBEAT.value, str)


# --- capability_match_score ---

class TestCapabilityMatchScore:
    def test_exact_match(self):
        assert capability_match_score(
            ["code", "test"], ["code", "test"]
        ) == 1.0

    def test_partial_match(self):
        score = capability_match_score(["code"], ["code", "test"])
        assert score == 0.5

    def test_no_match(self):
        assert capability_match_score(["code"], ["deploy"]) == 0.0

    def test_no_requirements(self):
        assert capability_match_score(["code"], []) == 0.5

    def test_extra_caps_no_penalty(self):
        assert capability_match_score(
            ["code", "test", "deploy"], ["code"]
        ) == 1.0

    def test_both_empty(self):
        assert capability_match_score([], []) == 0.5

    def test_agent_empty_required_nonempty(self):
        assert capability_match_score([], ["code"]) == 0.0
