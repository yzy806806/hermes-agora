"""Tests for PtyManager and PtyProcess."""
from __future__ import annotations

import asyncio
import os

import pytest

from agora_cli_bridge.pty_manager import PtyManager
from agora_cli_bridge.pty_process import PtyProcess


@pytest.fixture
def manager() -> PtyManager:
    return PtyManager()


@pytest.mark.asyncio
async def test_spawn_echo_and_read(manager: PtyManager) -> None:
    """Spawn cat subprocess, write input, read output."""
    proc = await manager.spawn_agent("echo-test", ["cat"])
    assert proc.is_alive()
    await proc.write_input("hello world\n")
    await asyncio.sleep(0.2)
    output = await proc.read_output()
    assert "hello world" in output
    await manager.terminate("echo-test")
    assert not proc.is_alive()


@pytest.mark.asyncio
async def test_spawn_duplicate_name_raises(manager: PtyManager) -> None:
    """Spawning with the same name twice should raise ValueError."""
    await manager.spawn_agent("dup", ["cat"])
    with pytest.raises(ValueError, match="already spawned"):
        await manager.spawn_agent("dup", ["cat"])
    await manager.terminate("dup")


@pytest.mark.asyncio
async def test_get_returns_process(manager: PtyManager) -> None:
    """get() returns the spawned process or None."""
    assert manager.get("missing") is None
    proc = await manager.spawn_agent("get-test", ["cat"])
    assert manager.get("get-test") is proc
    await manager.terminate("get-test")


@pytest.mark.asyncio
async def test_terminate_cleans_up(manager: PtyManager) -> None:
    """terminate() removes the process from the manager."""
    await manager.spawn_agent("cleanup", ["cat"])
    await manager.terminate("cleanup")
    assert manager.get("cleanup") is None


@pytest.mark.asyncio
async def test_terminate_all(manager: PtyManager) -> None:
    """terminate_all() stops all managed processes."""
    await manager.spawn_agent("a1", ["cat"])
    await manager.spawn_agent("a2", ["cat"])
    await manager.terminate_all()
    assert manager.get("a1") is None
    assert manager.get("a2") is None


@pytest.mark.asyncio
async def test_terminate_already_dead(manager: PtyManager) -> None:
    """terminate() on a dead process should not raise."""
    await manager.spawn_agent("dead", ["true"])
    await asyncio.sleep(0.2)
    await manager.terminate("dead")
