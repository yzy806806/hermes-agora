"""Tests for task_exec.py — state machine and WS handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_exec import (
    VALID_TRANSITIONS,
    _is_valid_transition,
    handle_task_status,
)


# --- _is_valid_transition ---

def test_all_valid_transitions():
    ok = [
        ("pending", "assigned"), ("assigned", "running"),
        ("assigned", "failed"), ("running", "done"),
        ("running", "failed"), ("done", "accepted"),
        ("done", "rejected"), ("rejected", "pending"),
        ("failed", "pending"),
    ]
    for cur, nxt in ok:
        assert _is_valid_transition(cur, nxt), f"{cur}->{nxt} should be valid"

def test_terminal_states_no_transitions():
    """Only 'accepted' is a true terminal state."""
    assert VALID_TRANSITIONS["accepted"] == set()
    assert not _is_valid_transition("accepted", "pending")
    # 'failed' can transition to 'pending' (Phase 10.1e retry path)
    assert "pending" in VALID_TRANSITIONS["failed"]

def test_invalid_transitions():
    bad = [
        ("pending", "running"), ("running", "assigned"),
        ("done", "pending"), ("accepted", "rejected"),
    ]
    for cur, nxt in bad:
        assert not _is_valid_transition(cur, nxt), (
            f"{cur}->{nxt} should be invalid")

# --- handle_task_status ---

@pytest.mark.asyncio
async def test_status_task_not_found():
    storage = AsyncMock()
    storage.get_task.return_value = None
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status("a1", {"task_id": "t1", "status": "running"},
                             storage, hub)
    hub.send.assert_called_once()
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "task_not_found"
