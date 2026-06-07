"""FastAPI application entry point for the Agora Coordinator service.

Assembles all modules, configures middleware, and provides lifespan
management (DB init on startup, cleanup on shutdown).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, cleanup on shutdown."""
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    storage = Storage(settings.db_path)
    await storage.init_db()
    state_machine = StateMachine(storage)
    init_deps(storage, state_machine)
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
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(bootstrap_router, prefix="/api/v1")
    app.include_router(bootstrap_extra_router, prefix="/api/v1")
    app.add_api_websocket_route("/ws/{agent_id}", websocket_endpoint)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()


def main() -> None:
    """Run the coordinator service via uvicorn."""
    uvicorn.run(
        "coordinator.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
