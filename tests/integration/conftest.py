"""Shared fixtures for e2e integration tests.

Starts a real Coordinator subprocess with a temp DB,
registers test agents via HTTP, and provides helper functions.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import tempfile
import time
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio


def _find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_health(
    port: int, timeout: float = 15.0
) -> None:
    """Poll /health until the coordinator is ready."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(
                    f"http://127.0.0.1:{port}/health",
                    timeout=2.0,
                )
                if r.status_code == 200:
                    return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        await asyncio.sleep(0.3)
    raise RuntimeError(
        f"Coordinator on port {port} not healthy after {timeout}s"
    )


@pytest_asyncio.fixture(scope="module")
async def coordinator_port() -> AsyncGenerator[int, None]:
    """Start a real Coordinator subprocess; yield its port."""
    port = _find_free_port()
    # Use a temp file since :memory: loses data across connections
    tmp_dir = tempfile.mkdtemp(prefix="agora_e2e_")
    db_path = os.path.join(tmp_dir, "agora.db")
    env = {
        **os.environ,
        "AGORA_DB_PATH": db_path,
        "AGORA_HOST": "127.0.0.1",
        "AGORA_PORT": str(port),
        "AGORA_LOG_LEVEL": "warning",
    }
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "coordinator.main",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for_health(port)
    yield port
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
    # Cleanup temp db
    try:
        os.unlink(db_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass


@pytest_asyncio.fixture
async def registered_agents(
    coordinator_port: int,
) -> list[dict]:
    """Register 5 test agents via HTTP; return their info dicts."""
    agents = []
    for i in range(5):
        aid = f"test-agent-{i}"
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"http://127.0.0.1:{coordinator_port}"
                "/api/v1/agents/register",
                json={
                    "agent_id": aid,
                    "name": f"Agent {i}",
                    "model": "test-model",
                    "role": "participant",
                },
            )
            assert r.status_code == 200, r.text
            agents.append(r.json())
    return agents
