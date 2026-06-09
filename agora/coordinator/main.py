"""FastAPI application entry point for the Agora Coordinator service.

Assembles all modules, configures middleware, and provides lifespan
management (DB init on startup, cleanup on shutdown).
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .tenant.router import router as tenant_router
from .tenant.router import init_tenant_deps
from .tenant.manager import TenantManager
from .storage.storage_manager import StorageManager
from .config import settings
from .router import init_deps, router
from .state import StateMachine
from .storage import Storage
from .ws_endpoint import websocket_endpoint
from .ws import manager
from .heartbeat import HeartbeatManager
from .timeout import TimeoutConfig, TimeoutManager
from .bootstrap import BootstrapConfig, BootstrapEngine
from .bootstrap.routes import router as bootstrap_router
from .bootstrap.routes_extra import router as bootstrap_extra_router
from .observability.metrics import init_metrics, metrics
from .observability.trace import set_trace_id
from .dashboard import router as dashboard_router
from .dashboard import init_dashboard_deps

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, cleanup on shutdown."""
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    # Phase 8.2: Multi-tenant StorageManager init
    data_dir = Path(os.path.dirname(settings.db_path) or "data")
    storage_mgr = StorageManager(data_dir)
    await storage_mgr.init()
    tenant_mgr = TenantManager(storage_mgr)
    init_tenant_deps(tenant_mgr)
    app.state.storage_mgr = storage_mgr
    app.state.tenant_mgr = tenant_mgr
    storage = Storage(settings.db_path)
    await storage.init_db()
    state_machine = StateMachine(storage)
    init_deps(storage, state_machine)
    # Observability init
    init_metrics()
    metrics.agents_connected.set(0)
    # Dashboard deps init
    init_dashboard_deps(storage)
    # Bootstrap engine init
    bootstrap_cfg = BootstrapConfig(db_path=settings.db_path)
    bootstrap_engine = BootstrapEngine(bootstrap_cfg)
    bootstrap_engine.init_routes()
    # Heartbeat & Timeout init
    heartbeat_mgr = HeartbeatManager(manager)
    timeout_cfg = TimeoutConfig(
        round_timeout=settings.round_timeout_seconds,
        vote_timeout=settings.vote_timeout_seconds,
        discussion_timeout=settings.discussion_timeout_seconds,
    )
    timeout_mgr = TimeoutManager(config=timeout_cfg)
    app.state.heartbeat_mgr = heartbeat_mgr
    app.state.timeout_mgr = timeout_mgr
    await heartbeat_mgr.start_heartbeat(interval=settings.heartbeat_interval_seconds)
    logger.info("Coordinator started (db=%s)", settings.db_path)
    yield
    # Cleanup
    await heartbeat_mgr.stop()
    logger.info("Coordinator shutting down")


def create_app() -> FastAPI:
    """Factory: create and configure the FastAPI application."""
    app = FastAPI(
        title="Hermes Agora Coordinator",
        version="0.8.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        """Inject X-Trace-Id into every HTTP request context."""
        trace_id = request.headers.get(
            "X-Trace-Id", str(uuid.uuid4()))
        set_trace_id(trace_id)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response
    app.include_router(tenant_router, prefix="/api/v1")
    app.include_router(router, prefix="/api/v1")
    app.include_router(bootstrap_router, prefix="/api/v1")
    app.include_router(bootstrap_extra_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.add_api_websocket_route("/ws/{agent_id}", websocket_endpoint)
    # Phase 8.2: tenant-scoped WS (backward compat via default tenant_id)
    # Dashboard static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/dashboard")
    async def dashboard_page():
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "dashboard.html")

    @app.get("/health")
    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()


def main() -> None:
    """Run the coordinator service via uvicorn."""
    uvicorn.run(
        "agora.coordinator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
