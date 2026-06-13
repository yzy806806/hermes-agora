"""Phase 13.7d: Runtime deployment smoke tests.

Tests that require a running coordinator subprocess.
Uses the same pattern as tests/integration/conftest.py.
"""
from __future__ import annotations

import asyncio
import os
import socket
import tempfile
import time
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _wait_for_health(port: int, timeout: float = 15.0) -> None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"http://127.0.0.1:{port}/api/v1/health", timeout=2.0)
                if r.status_code == 200:
                    return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        await asyncio.sleep(0.3)
    raise RuntimeError(f"Coordinator not healthy after {timeout}s")


@pytest_asyncio.fixture(scope="module")
async def deploy_port() -> AsyncGenerator[int, None]:
    port = _find_free_port()
    tmp_dir = tempfile.mkdtemp(prefix="agora_deploy_")
    db_path = os.path.join(tmp_dir, "agora.db")
    env = {
        **os.environ,
        "AGORA_DB_PATH": db_path,
        "AGORA_HOST": "127.0.0.1",
        "AGORA_PORT": str(port),
        "AGORA_LOG_LEVEL": "warning",
        "AGORA_REQUIRE_APPROVAL": "false",
    }
    proc = await asyncio.create_subprocess_exec(
        "uv", "run", "python", "-m", "agora.coordinator.main",
        env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    await _wait_for_health(port)
    yield port
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
