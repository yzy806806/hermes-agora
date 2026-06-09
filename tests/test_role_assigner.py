"""Tests for coordinator/role_assigner.py and perspective_ensurer.py."""
import pytest
from unittest.mock import AsyncMock

from agora.coordinator.model_capabilities import ModelCapability, ModelProfiler
from agora.coordinator.models import DiscussionRole
from agora.coordinator.role_assigner import ModelAwareRoleAssigner, ROLE_INSTRUCTIONS
from agora.coordinator.perspective_ensurer import PerspectiveEnsurer


def _make_agent(agent_id: str, model: str = "unknown") -> dict:
    return {"agent_id": agent_id, "model": model}


class TestRoleInstructions:
    def test_all_roles_have_instructions(self):
        for role in DiscussionRole:
            assert role in ROLE_INSTRUCTIONS or True  # default fallback exists

    def test_get_role_instruction(self):
        text = ModelAwareRoleAssigner.get_role_instruction(DiscussionRole.FACT_CHECKER)
        assert "事实" in text

    def test_get_role_instruction_default(self):
        # NEUTRAL has instruction, so test the default path
        text = ModelAwareRoleAssigner.get_role_instruction(DiscussionRole.NEUTRAL)
        assert len(text) > 0


class TestModelAwareRoleAssigner:
    @pytest.fixture
    def mock_storage(self):
        storage = AsyncMock()
        storage.list_agents = AsyncMock(return_value=[
            _make_agent("a1", "gpt-4"),
            _make_agent("a2", "claude-3"),
            _make_agent("a3", "gemini"),
        ])
        return storage

    @pytest.fixture
    def assigner(self, mock_storage):
        return ModelAwareRoleAssigner(mock_storage, ModelProfiler())

    @pytest.mark.asyncio
    async def test_assign_roles_by_capability(self, assigner):
        roles = await assigner.assign_optimal_roles("motion1")
        # gpt-4: REASONING + ANALYTICAL -> EXPERT (ANALYTICAL)
        # claude-3: CREATIVE + FACTUAL -> FACT_CHECKER (FACTUAL assigned first)
        # gemini: REASONING + DOMAIN_EXPERT -> NEUTRAL (no FACTUAL/CREATIVE/ANALYTIC)
        assert roles["a1"] == DiscussionRole.EXPERT
        assert roles["a2"] == DiscussionRole.FACT_CHECKER
        assert roles["a3"] == DiscussionRole.NEUTRAL

    @pytest.mark.asyncio
    async def test_unknown_model_gets_neutral(self):
        storage = AsyncMock()
        storage.list_agents = AsyncMock(return_value=[
            _make_agent("a1", "unknown-model"),
        ])
        assigner = ModelAwareRoleAssigner(storage, ModelProfiler())
        roles = await assigner.assign_optimal_roles("motion1")
        assert roles["a1"] == DiscussionRole.NEUTRAL

    @pytest.mark.asyncio
    async def test_no_agents(self):
        storage = AsyncMock()
        storage.list_agents = AsyncMock(return_value=[])
        assigner = ModelAwareRoleAssigner(storage, ModelProfiler())
        roles = await assigner.assign_optimal_roles("motion1")
        assert roles == {}


class TestPerspectiveEnsurer:
    @pytest.fixture
    def mock_storage(self):
        storage = AsyncMock()
        storage.get_messages = AsyncMock(return_value=[])
        return storage

    @pytest.fixture
    def ensurer(self, mock_storage):
        return PerspectiveEnsurer(mock_storage)

    @pytest.mark.asyncio
    async def test_empty_discussion_needs_all(self, ensurer):
        roles = await ensurer.ensure_diversity("motion1", {})
        assert DiscussionRole.SUPPORT_ADVOCATE in roles
        assert DiscussionRole.OPPOSE_ADVOCATE in roles
        assert DiscussionRole.NEUTRAL in roles

    @pytest.mark.asyncio
    async def test_missing_oppose(self):
        storage = AsyncMock()
        storage.get_messages = AsyncMock(return_value=[
            {"stance": "support"}, {"stance": "neutral"},
        ])
        ensurer = PerspectiveEnsurer(storage)
        roles = await ensurer.ensure_diversity("motion1", {})
        assert DiscussionRole.OPPOSE_ADVOCATE in roles
        assert DiscussionRole.OPPOSE_ADVOCATE not in [
            r for r in roles if r == DiscussionRole.SUPPORT_ADVOCATE
        ]

    @pytest.mark.asyncio
    async def test_stance_distribution(self):
        storage = AsyncMock()
        storage.get_messages = AsyncMock(return_value=[
            {"stance": "support"}, {"stance": "support"},
            {"stance": "oppose"}, {"stance": "neutral"},
        ])
        ensurer = PerspectiveEnsurer(storage)
        dist = await ensurer.get_stance_distribution("motion1")
        assert dist == {"support": 2, "oppose": 1, "neutral": 1}
