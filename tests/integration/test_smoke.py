"""Smoke test: verify the integration test infrastructure works.

This test simply checks that the coordinator fixture can start a
real Coordinator subprocess and that the /health endpoint responds.
It does NOT test any business logic — that belongs in test_e2e_*.py.
"""
from __future__ import annotations

import pytest

import httpx


@pytest.mark.integration
async def test_coordinator_fixture_starts(coordinator_port: int) -> None:
    """The coordinator fixture should yield a working port."""
    assert isinstance(coordinator_port, int)
    assert coordinator_port > 0


@pytest.mark.integration
async def test_health_endpoint(coordinator_port: int) -> None:
    """The /health endpoint should return 200."""
    url = f"http://127.0.0.1:{coordinator_port}/health"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=5.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "healthy"
