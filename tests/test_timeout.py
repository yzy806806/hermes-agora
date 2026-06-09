"""Tests for coordinator/timeout.py — TimeoutManager and TimeoutConfig."""

from __future__ import annotations

import asyncio

import pytest

from agora.coordinator.timeout import TimeoutAction, TimeoutConfig, TimeoutManager


# -- TimeoutConfig --


def test_default_config():
    cfg = TimeoutConfig()
    assert cfg.round_timeout == 300
    assert cfg.vote_timeout == 120
    assert cfg.discussion_timeout == 1800


def test_custom_config():
    cfg = TimeoutConfig(round_timeout=60, vote_timeout=30, discussion_timeout=600)
    assert cfg.round_timeout == 60
    assert cfg.vote_timeout == 30


# -- TimeoutAction enum --


def test_timeout_action_values():
    assert TimeoutAction.FORCE_VOTE == "force_vote"
    assert TimeoutAction.END_DISCUSSION == "end_discussion"
    assert TimeoutAction.EXTEND_ROUND == "extend_round"


# -- TimeoutManager --


@pytest.mark.asyncio
async def test_start_round_timeout():
    mgr = TimeoutManager()
    mgr.start_round_timeout("m1", timeout_seconds=1)
    assert mgr.get_remaining_time("m1") is not None
    mgr.cancel_timeout("m1")
    assert mgr.get_remaining_time("m1") is None


@pytest.mark.asyncio
async def test_start_vote_timeout_fires():
    fired: list[tuple[str, TimeoutAction]] = []

    async def on_timeout(motion_id: str, action: TimeoutAction) -> None:
        fired.append((motion_id, action))

    mgr = TimeoutManager(on_timeout=on_timeout)
    mgr.start_vote_timeout("m2", timeout_seconds=1)
    await asyncio.sleep(1.2)
    assert len(fired) == 1
    assert fired[0][0] == "m2"
    assert fired[0][1] == TimeoutAction.END_DISCUSSION


@pytest.mark.asyncio
async def test_cancel_timeout():
    fired: list[tuple[str, TimeoutAction]] = []

    async def on_timeout(motion_id: str, action: TimeoutAction) -> None:
        fired.append((motion_id, action))

    mgr = TimeoutManager(on_timeout=on_timeout)
    mgr.start_round_timeout("m3", timeout_seconds=1)
    mgr.cancel_timeout("m3")
    await asyncio.sleep(1.2)
    assert len(fired) == 0


@pytest.mark.asyncio
async def test_get_remaining_time():
    mgr = TimeoutManager()
    assert mgr.get_remaining_time("m4") is None
    mgr.start_round_timeout("m4", timeout_seconds=10)
    remaining = mgr.get_remaining_time("m4")
    assert remaining is not None
    assert 8 <= remaining <= 10
    mgr.cancel_timeout("m4")


@pytest.mark.asyncio
async def test_handle_timeout():
    mgr = TimeoutManager()
    mgr.start_round_timeout("m5", timeout_seconds=1)
    action = await mgr.handle_timeout("m5")
    assert action == TimeoutAction.FORCE_VOTE


@pytest.mark.asyncio
async def test_replace_timer():
    mgr = TimeoutManager()
    mgr.start_round_timeout("m6", timeout_seconds=100)
    mgr.start_vote_timeout("m6", timeout_seconds=1)
    remaining = mgr.get_remaining_time("m6")
    assert remaining is not None
    assert remaining <= 2
    mgr.cancel_timeout("m6")
