"""Dashboard API routes: events, SSE stream, discussion timeline, audit query.

Serves the event history, real-time event stream via SSE,
discussion timeline for the dashboard frontend, and audit log query.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .audit import AuditEventType, AuditLogger
from .dashboard_models import AuditEventItem, AuditQueryResponse
from .models import EventResponse, TimelineEntry
from .rbac import Permission, Role, get_current_role, requires
from .storage import Storage

logger = logging.getLogger(__name__)

router = APIRouter()

_storage: Optional[Storage] = None
_audit_logger: Optional[AuditLogger] = None


def init_dashboard_deps(storage: Storage) -> None:
    """Initialize dashboard dependencies. Called at app startup."""
    global _storage
    _storage = storage


def init_audit_deps(audit_logger: AuditLogger) -> None:
    """Initialize audit logger dependency. Called at app startup."""
    global _audit_logger
    _audit_logger = audit_logger


def _get_storage() -> Storage:
    if _storage is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _storage


def _get_audit_logger() -> AuditLogger:
    if _audit_logger is None:
        raise HTTPException(status_code=503, detail="Audit not initialized")
    return _audit_logger


@router.get("/events", response_model=list[EventResponse])
async def get_events(
    since: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
) -> list[EventResponse]:
    """Return recent events, optionally filtered by time and type."""
    storage = _get_storage()
    rows = await storage.get_events(since=since, event_type=type, limit=limit)
    return [
        EventResponse(
            event_id=r.get("id", 0),
            type=r.get("type", ""),
            detail=r.get("detail", ""),
            motion_id=r.get("motion_id"),
            agent_id=r.get("agent_id"),
            created_at=r.get("created_at", ""),
        )
        for r in rows
    ]


@router.get("/events/stream")
async def events_stream(request: Request) -> StreamingResponse:
    """SSE endpoint: push new events to connected clients."""
    storage = _get_storage()

    async def generate():
        last_id = 0
        while True:
            if await request.is_disconnected():
                break
            rows = await storage.get_events(limit=20)
            new = [r for r in rows if r.get("id", 0) > last_id]
            for r in new:
                last_id = r["id"]
                yield f"data: {json.dumps(r)}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/discussions/{motion_id}/timeline", response_model=list[TimelineEntry])
async def get_timeline(motion_id: str) -> list[TimelineEntry]:
    """Return the discussion timeline for a specific motion."""
    storage = _get_storage()
    motion = await storage.get_motion(motion_id)
    if motion is None:
        raise HTTPException(status_code=404, detail="Motion not found")
    entries = await storage.get_timeline(motion_id)
    return [
        TimelineEntry(
            time=e.get("time", ""),
            type=e.get("type", ""),
            agent_id=e.get("agent_id"),
            content=e.get("content", ""),
            round_num=e.get("round_num"),
        )
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Audit Query API (Phase 11.1d)
# ---------------------------------------------------------------------------


def _parse_iso(val: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp string, return None if empty."""
    if not val:
        return None
    return datetime.fromisoformat(val)


def _parse_event_type(val: Optional[str]) -> Optional[AuditEventType]:
    """Parse event_type query param into AuditEventType enum."""
    if not val:
        return None
    try:
        return AuditEventType(val)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type: {val}",
        )


@router.get("/admin/audit", response_model=AuditQueryResponse)
@requires(Permission.ADMIN_FULL)
async def query_audit_log(
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    event_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _rbac_role: Role | None = Depends(get_current_role),
) -> AuditQueryResponse:
    """Query audit log with filters and pagination. Admin only."""
    audit = _get_audit_logger()
    et = _parse_event_type(event_type)
    since_dt = _parse_iso(since)
    until_dt = _parse_iso(until)
    total = await audit.count_events(
        actor_id=actor_id, action=action, event_type=et,
        tenant_id=tenant_id, since=since_dt, until=until_dt,
    )
    rows = await audit.query_events(
        actor_id=actor_id, action=action, event_type=et,
        tenant_id=tenant_id, since=since_dt, until=until_dt,
        limit=limit, offset=offset,
    )
    events = [
        AuditEventItem(
            id=r.get("id", 0),
            event_type=r.get("event_type", ""),
            actor_id=r.get("actor_id", ""),
            actor_role=r.get("actor_role", ""),
            action=r.get("action", ""),
            resource=r.get("resource", ""),
            details=json.loads(r.get("details_json", "{}")),
            timestamp=r.get("timestamp", ""),
            tenant_id=r.get("tenant_id", "default"),
        )
        for r in rows
    ]
    return AuditQueryResponse(
        events=events, total=total, limit=limit, offset=offset,
    )
