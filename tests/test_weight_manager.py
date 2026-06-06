"""Tests for WeightManager."""

import pytest
from unittest.mock import AsyncMock

from coordinator.voting.weight_manager import WeightManager, WeightSource


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.list_agents.return_value = [
        {"agent_id": "a1", "capabilities": ["security"]},
        {"agent_id": "a2", "capabilities": ["backend"]},
    ]
    storage.get_motion.return_value = {"context": "security,infra"}
    return storage


class TestWeightManagerDefault:
    """Default strategy: equal weights."""

    def test_default_weight(self):
        assert WeightManager.DEFAULT_WEIGHT == 1.0

    @pytest.mark.asyncio
    async def test_equal_weights(self, mock_storage):
        wm = WeightManager(mock_storage, {})
        weights = await wm.get_weights("m1")
        assert weights == {"a1": 1.0, "a2": 1.0}

    @pytest.mark.asyncio
    async def test_cached_weights(self, mock_storage):
        wm = WeightManager(mock_storage, {})
        w1 = await wm.get_weights("m1")
        w2 = await wm.get_weights("m1")
        assert w1 is w2
        mock_storage.list_agents.assert_called_once()


class TestWeightManagerManual:
    """Manual weight strategy."""

    @pytest.mark.asyncio
    async def test_manual_weights(self, mock_storage):
        config = {
            "weight_strategy": WeightSource.MANUAL,
            "manual_weights": {"a1": 2.0, "a2": 0.5},
        }
        wm = WeightManager(mock_storage, config)
        weights = await wm.get_weights("m1")
        assert weights == {"a1": 2.0, "a2": 0.5}


class TestWeightManagerExpertise:
    """Expertise-based weight strategy."""

    @pytest.mark.asyncio
    async def test_expertise_weights(self, mock_storage):
        config = {"weight_strategy": WeightSource.EXPERTISE}
        wm = WeightManager(mock_storage, config)
        weights = await wm.get_weights("m1")
        # a1 has "security" matching "security" in context -> 1.0 + 0.5
        assert weights["a1"] == 1.5
        # a2 has "backend" not matching -> 1.0
        assert weights["a2"] == 1.0


class TestWeightManagerCache:
    """Cache clearing."""

    @pytest.mark.asyncio
    async def test_clear_single(self, mock_storage):
        wm = WeightManager(mock_storage, {})
        await wm.get_weights("m1")
        wm.clear_cache("m1")
        await wm.get_weights("m1")
        assert mock_storage.list_agents.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_all(self, mock_storage):
        wm = WeightManager(mock_storage, {})
        await wm.get_weights("m1")
        wm.clear_cache()
        await wm.get_weights("m1")
        assert mock_storage.list_agents.call_count == 2
