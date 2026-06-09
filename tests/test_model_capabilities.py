"""Tests for coordinator/model_capabilities.py."""
import pytest
from agora.coordinator.model_capabilities import (
    ModelCapability,
    ModelProfile,
    MODEL_PROFILES,
    ModelProfiler,
)


class TestModelCapability:
    def test_flag_values(self):
        assert ModelCapability.REASONING_STRONG.value == 1
        assert ModelCapability.CREATIVE.value == 2
        assert ModelCapability.FACTUAL.value == 4
        assert ModelCapability.ANALYTICAL.value == 8
        assert ModelCapability.DOMAIN_EXPERT.value == 16

    def test_flag_combination(self):
        combined = ModelCapability.REASONING_STRONG | ModelCapability.ANALYTICAL
        assert ModelCapability.REASONING_STRONG in combined
        assert ModelCapability.ANALYTICAL in combined
        assert ModelCapability.CREATIVE not in combined

    def test_empty_capability(self):
        empty = ModelCapability(0)
        assert ModelCapability.REASONING_STRONG not in empty


class TestModelProfile:
    def test_defaults(self):
        p = ModelProfile(model_name="test", capabilities=ModelCapability(0))
        assert p.preferred_stance is None
        assert p.weaknesses == []

    def test_with_all_fields(self):
        p = ModelProfile(
            model_name="test",
            capabilities=ModelCapability.CREATIVE,
            preferred_stance="neutral",
            weaknesses=["too creative"],
        )
        assert p.preferred_stance == "neutral"
        assert "too creative" in p.weaknesses


class TestModelProfiles:
    def test_gpt4_profile(self):
        p = MODEL_PROFILES["gpt-4"]
        assert ModelCapability.REASONING_STRONG in p.capabilities
        assert ModelCapability.ANALYTICAL in p.capabilities

    def test_claude3_profile(self):
        p = MODEL_PROFILES["claude-3"]
        assert ModelCapability.CREATIVE in p.capabilities
        assert ModelCapability.FACTUAL in p.capabilities
        assert p.preferred_stance == "neutral"

    def test_gemini_profile(self):
        p = MODEL_PROFILES["gemini"]
        assert ModelCapability.DOMAIN_EXPERT in p.capabilities


class TestModelProfiler:
    def test_get_known_profile(self):
        profiler = ModelProfiler()
        p = profiler.get_profile("gpt-4")
        assert p.model_name == "gpt-4"
        assert ModelCapability.REASONING_STRONG in p.capabilities

    def test_get_profile_case_insensitive(self):
        profiler = ModelProfiler()
        p = profiler.get_profile("GPT-4")
        # Lookup is case-insensitive, returns preset profile
        assert ModelCapability.REASONING_STRONG in p.capabilities

    def test_get_unknown_profile(self):
        profiler = ModelProfiler()
        p = profiler.get_profile("unknown-model")
        assert p.model_name == "unknown-model"
        assert p.capabilities == ModelCapability(0)

    def test_get_empty_model_name(self):
        profiler = ModelProfiler()
        p = profiler.get_profile("")
        assert p.model_name == "unknown"

    @pytest.mark.asyncio
    async def test_infer_capabilities_from_storage(self):
        profiler = ModelProfiler()
        from unittest.mock import AsyncMock
        mock_storage = AsyncMock()
        mock_storage.get_agent = AsyncMock(return_value={"model": "gpt-4"})
        p = await profiler.infer_capabilities("agent1", mock_storage)
        assert ModelCapability.REASONING_STRONG in p.capabilities

    @pytest.mark.asyncio
    async def test_infer_capabilities_no_agent(self):
        profiler = ModelProfiler()
        from unittest.mock import AsyncMock
        mock_storage = AsyncMock()
        mock_storage.get_agent = AsyncMock(return_value=None)
        p = await profiler.infer_capabilities("agent1", mock_storage)
        assert p.capabilities == ModelCapability(0)
