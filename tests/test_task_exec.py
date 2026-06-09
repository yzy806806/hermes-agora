"""Tests for task_exec.py — state machine and WS handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agora.coordinator.task_exec import (
    VALID_TRANSITIONS,
    _is_valid_transition,
    handle_task_status,
    handle_task_accept_result,
)


# --- _is_valid_transition ---

def test_all_valid_transitions():
    ok = [
        ("pending", "assigned"), ("assigned", "running"),
        ("assigned", "failed"), ("running", "done"),
        ("running", "failed"), ("done", "accepted"),
        ("done", "rejected"), ("rejected", "pending"),
    ]
    for cur, nxt in ok:
        assert _is_valid_transition(cur, nxt), f"{cur}->{nxt} should be valid"


def test_terminal_states_no_transitions():
    for terminal in ("failed", "accepted"):
        assert VALID_TRANSITIONS[terminal] == set()
        assert not _is_valid_transition(terminal, "pending")


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


@pytest.mark.asyncio
async def test_status_invalid_transition():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "pending", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status("a1", {"task_id": "t1", "status": "done"},
                             storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "invalid_transition"


@pytest.mark.asyncio
async def test_status_done_triggers_verify():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "running", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    with patch("agora.coordinator.task_exec.verify_task",
               new_callable=AsyncMock) as mock_verify:
        await handle_task_status(
            "a1", {"task_id": "t1", "status": "done"}, storage, hub)
        mock_verify.assert_called_once_with("t1", storage, hub)


@pytest.mark.asyncio
async def test_status_failed_logs_event():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "running", "motion_id": "m1"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status(
        "a1", {"task_id": "t1", "status": "failed", "error": "boom"},
        storage, hub)
    storage.log_event.assert_called_once_with(
        "task.failed", "Task t1 failed: boom",
        motion_id="m1", agent_id="a1")


@pytest.mark.asyncio
async def test_status_missing_status():
    storage = AsyncMock()
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_status("a1", {"task_id": "t1"}, storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "missing_status"


# --- handle_task_accept_result ---

@pytest.mark.asyncio
async def test_accept_result_accepted():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "done"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": True}, storage, hub)
    calls = storage.update_task_status.call_args_list
    assert calls[0][0] == ("t1", "accepted")


@pytest.mark.asyncio
async def test_accept_result_rejected_requeues():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "done"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": False}, storage, hub)
    calls = storage.update_task_status.call_args_list
    assert calls[0][0] == ("t1", "rejected")
    assert calls[1][0] == ("t1", "pending")


@pytest.mark.asyncio
async def test_accept_result_wrong_state():
    storage = AsyncMock()
    storage.get_task.return_value = {"status": "running"}
    hub = MagicMock()
    hub.send = AsyncMock()
    await handle_task_accept_result(
        "rev1", {"task_id": "t1", "accepted": True}, storage, hub)
    msg = hub.send.call_args[0][1]
    assert msg["payload"]["code"] == "invalid_transition"
