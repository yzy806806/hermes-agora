"""Integration tests for Phase 8: verify all modules assembled in main.py."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path


def test_app_version_is_0_8():
    """Verify FastAPI app version bumped to 0.8.0."""
    from coordinator.main import create_app
    app = create_app()
    assert app.version == "0.8.0"


def test_tenant_router_mounted():
    """Verify tenant router is included under /api/v1."""
    from coordinator.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert any("/api/v1/tenants" in r for r in routes)


def test_dashboard_router_mounted():
    """Verify dashboard router is included under /api/v1."""
    from coordinator.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert any("/api/v1/events" in r for r in routes)


def test_dashboard_page_route_exists():
    """Verify /dashboard HTML route exists."""
    from coordinator.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/dashboard" in routes


def test_health_endpoint_exists():
    """Verify /health endpoint still works (backward compat)."""
    from coordinator.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    assert "/health" in routes


def test_ws_endpoint_exists():
    """Verify WebSocket endpoint exists."""
    from coordinator.main import create_app
    app = create_app()
    ws_routes = [
        r.path for r in app.routes
        if hasattr(r, 'path') and '/ws' in r.path
    ]
    assert len(ws_routes) > 0