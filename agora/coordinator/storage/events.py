"""Event log storage for the Agora dashboard.

Stores and queries system events (motion lifecycle, agent connections, etc.)
for the dashboard event stream and SSE endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


async def log_event(
    db, event_type: str, detail: str = "",
    motion_id: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> int:
    """Insert a new event into the event log."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute(
        """INSERT INTO events (type, detail, motion_id, agent_id, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        [event_type, detail, motion_id, agent_id, now],
    )
    await db.commit()
    return cursor.lastrowid


async def get_events(
    db, since: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Query events with optional filters."""
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("created_at > ?")
        params.append(since)
    if event_type:
        clauses.append("type = ?")
        params.append(event_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    rows = await db.execute_fetchall(
        f"SELECT * FROM events {where} ORDER BY created_at DESC LIMIT ?",
        params,
    )
    return [dict(r) for r in rows]


async def get_timeline(db, motion_id: str) -> list[dict]:
    """Build a discussion timeline from messages + votes + status changes."""
    entries: list[dict] = []
    # Status-change events
    rows = await db.execute_fetchall(
        "SELECT * FROM events WHERE motion_id = ? ORDER BY created_at",
        [motion_id],
    )
    for r in rows:
        entries.append(dict(r))
    # Messages (column: timestamp, not created_at)
    msgs = await db.execute_fetchall(
        "SELECT * FROM messages WHERE motion_id = ? ORDER BY timestamp",
        [motion_id],
    )
    for m in msgs:
        d = dict(m)
        entries.append({
            "time": d.get("timestamp", ""),
            "type": "speech",
            "agent_id": d.get("agent_id"),
            "content": d.get("content", ""),
            "round_num": d.get("round_num"),
        })
    # Votes (column: timestamp, not created_at)
    votes = await db.execute_fetchall(
        "SELECT * FROM votes WHERE motion_id = ? ORDER BY timestamp",
        [motion_id],
    )
    for v in votes:
        d = dict(v)
        entries.append({
            "time": d.get("timestamp", ""),
            "type": "vote",
            "agent_id": d.get("agent_id"),
            "content": f"voted {d.get('vote', '?')} (confidence {d.get('confidence', 0)})",
        })
    entries.sort(key=lambda e: e.get("time", ""))
    return entries
