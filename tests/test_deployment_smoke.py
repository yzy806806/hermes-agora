"""Phase 13.7d: Runtime deployment smoke tests — test functions.

Requires deploy_port fixture from test_deployment_runtime.py.
Run: pytest tests/test_deployment_runtime.py -v
"""
from __future__ import annotations

import pytest
import httpx

from test_deployment_runtime import deploy_port


@pytest.mark.asyncio
async def test_coordinator_accessible_on_port(deploy_port: int) -> None:
    """Coordinator is reachable on the configured port."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"http://127.0.0.1:{deploy_port}/api/v1/health", timeout=5.0)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_healthy(deploy_port: int) -> None:
    """Health endpoint returns status=healthy with all fields."""
    async with httpx.AsyncClient() as c:
        r = await c.get(f"http://127.0.0.1:{deploy_port}/api/v1/health", timeout=5.0)
    data = r.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.13.0"
    for field in ("uptime_seconds", "agents_connected", "tenants", "db_size_mb"):
        assert field in data, f"missing field: {field}"


@pytest.mark.asyncio
async def test_legacy_health_redirect(deploy_port: int) -> None:
    """Legacy /health endpoint still works for backward compat."""
    async with httpx.AsyncClient(follow_redirects=True) as c:
        r = await c.get(f"http://127.0.0.1:{deploy_port}/health", timeout=5.0)
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
