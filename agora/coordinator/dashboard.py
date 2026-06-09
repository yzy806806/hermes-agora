"""Dashboard API routes: events, SSE stream, discussion timeline.

Serves the event history, real-time event stream via SSE,
and discussion timeline for the dashboard frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .models import EventResponse, TimelineEntry
from .storage import Storage

logger = logging.getLogger(__name__)

router = APIRouter()

_storage: Optional[Storage] = None


def init_dashboard_deps(storage: Storage) -> None:
    """Initialize dashboard dependencies. Called at app startup."""
    global _storage
    _storage = storage


def _get_storage() -> Storage:
    if _storage is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _storage


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
