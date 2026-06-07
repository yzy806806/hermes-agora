"""Tests for DynamicRoundManager — adaptive round control."""
import pytest

from coordinator.assessment import ConsensusLevel
from coordinator.dynamic_rounds import DynamicRoundManager, RoundConfig
from coordinator.storage import Storage


async def _seed_motion(
    storage: Storage, current_round: int = 0,
) -> str:
    """Create a motion and return its id."""
    motion = await storage.create_motion("T", "D", rounds=5)
    mid = motion["id"]
    if current_round > 0:
        for _ in range(current_round):
            await storage.increment_round(mid)
    return mid


@pytest.mark.asyncio
async def test_min_rounds_not_met(storage: Storage):
    """Below min_rounds, always continue."""
    mid = await _seed_motion(storage, current_round=1)
    mgr = DynamicRoundManager(RoundConfig(min_rounds=2))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.9, ConsensusLevel.HIGH,
    )
    assert cont is True
    assert reason == "min_rounds_not_met"


@pytest.mark.asyncio
async def test_consensus_reached(storage: Storage):
    """High consensus after min_rounds stops discussion."""
    mid = await _seed_motion(storage, current_round=2)
    mgr = DynamicRoundManager(RoundConfig(min_rounds=2))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.3, ConsensusLevel.HIGH,
    )
    assert cont is False
    assert reason == "consensus_reached"


@pytest.mark.asyncio
async def test_quality_sufficient(storage: Storage):
    """Quality above threshold stops discussion."""
    mid = await _seed_motion(storage, current_round=3)
    mgr = DynamicRoundManager(RoundConfig(
        min_rounds=2, quality_threshold=0.7,
    ))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.8, ConsensusLevel.MODERATE,
    )
    assert cont is False
    assert reason == "quality_sufficient"


@pytest.mark.asyncio
async def test_max_rounds_reached(storage: Storage):
    """Hard cap forces stop regardless of quality."""
    mid = await _seed_motion(storage, current_round=5)
    mgr = DynamicRoundManager(RoundConfig(max_rounds=5))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.3, ConsensusLevel.LOW,
    )
    assert cont is False
    assert reason == "max_rounds_reached"


@pytest.mark.asyncio
async def test_adaptive_quality_low_extend(storage: Storage):
    """Low quality with adaptive extends rounds."""
    mid = await _seed_motion(storage, current_round=3)
    mgr = DynamicRoundManager(RoundConfig(
        min_rounds=2, adaptive=True, low_quality_threshold=0.4,
    ))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.2, ConsensusLevel.MODERATE,
    )
    assert cont is True
    assert reason == "quality_low_extend"


@pytest.mark.asyncio
async def test_adaptive_disabled(storage: Storage):
    """Without adaptive, low quality does not extend."""
    mid = await _seed_motion(storage, current_round=3)
    mgr = DynamicRoundManager(RoundConfig(
        min_rounds=2, adaptive=False, quality_threshold=0.7,
    ))
    cont, reason = await mgr.should_continue(
        mid, storage, 0.2, ConsensusLevel.MODERATE,
    )
    assert cont is True
    assert reason == "continue"


@pytest.mark.asyncio
async def test_motion_not_found(storage: Storage):
    """Non-existent motion returns False."""
    mgr = DynamicRoundManager()
    cont, reason = await mgr.should_continue(
        "nonexistent", storage, 0.5, ConsensusLevel.LOW,
    )
    assert cont is False
    assert reason == "motion_not_found"


@pytest.mark.asyncio
async def test_default_config(storage: Storage):
    """Default config continues when no special condition met."""
    mid = await _seed_motion(storage, current_round=2)
    mgr = DynamicRoundManager()
    cont, reason = await mgr.should_continue(
        mid, storage, 0.5, ConsensusLevel.MODERATE,
    )
    assert cont is True
    assert reason == "continue"
